import random
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update, insert
from models import Projeto, KanbanConfig, KanbanHistorico

class PhaseTransitionError(Exception):
    """Erro lançado quando uma transição de fase viola as regras de negócio."""
    pass

class KanbanService:
    def __init__(self, db: Session):
        self.db = db
        # Whitelist de colunas que podem ser mapeadas
        self.mappable_columns = [
            "nome", "documento", "fee", "moeda", "squad_atribuida", 
            "produto_contratado", "data_de_inicio", "cohort", 
            "meta_account_id", "google_account_id", "url_webhook_gchat",
            "step", "informacoes_gerais", "orcamento_midia_meta", 
            "orcamento_midia_google", "data_fim", "ekyte_workspace"
        ]

    def get_board_config(self, slug: str = "fluxo-projetos") -> Optional[Dict[str, Any]]:
        """Retorna a configuração de um board Kanban pelo slug."""
        stmt = select(KanbanConfig).where(KanbanConfig.slug == slug)
        result = self.db.execute(stmt).scalar_one_or_none()
        
        if not result:
            # Inicializa com configuração padrão se não existir (Seed)
            return self._seed_default_config(slug)
            
        return result.configuracao

    def _seed_default_config(self, slug: str) -> Dict[str, Any]:
        """Cria uma configuração padrão para o Kanban."""
        default_config = {
            "nome": "Fluxo de Projetos",
            "fases": [
                {
                    "id": "onboarding",
                    "nome": "Onboarding",
                    "ordem": 1,
                    "cor": "#3498db",
                    "status_do_projeto": "Ativo",
                    "campos": [
                        {"id": "responsavel", "label": "Responsável", "tipo": "string", "obrigatorio": True},
                        {"id": "data_kickoff", "label": "Data Kickoff", "tipo": "date"}
                    ]
                },
                {
                    "id": "execucao",
                    "nome": "Execução",
                    "ordem": 2,
                    "cor": "#f1c40f",
                    "status_do_projeto": "Ativo",
                    "campos": [
                        {"id": "prioridade", "label": "Prioridade", "tipo": "select", "opcoes": ["Baixa", "Média", "Alta"]}
                    ]
                },
                {
                    "id": "concluido",
                    "nome": "Concluído",
                    "ordem": 3,
                    "cor": "#2ecc71",
                    "status_do_projeto": "Ativo",
                    "campos": [
                        {"id": "data_entrega", "label": "Data de Entrega", "tipo": "date"}
                    ],
                    "permite_acesso_direto": True
                },
                {
                    "id": "churn",
                    "nome": "Churn",
                    "ordem": 99,
                    "cor": "#e74c3c",
                    "status_do_projeto": "Inativo",
                    "campos": [
                        {"id": "motivo", "label": "Motivo do Churn", "tipo": "text", "obrigatorio": True}
                    ],
                    "permite_acesso_direto": True
                }
            ]
        }
        
        new_config = KanbanConfig(
            slug=slug,
            configuracao=default_config
        )
        self.db.add(new_config)
        self.db.commit()
        return default_config

    def list_cards(self, slug: str = "fluxo-projetos") -> List[Dict[str, Any]]:
        """Lista todos os projetos formatados como cards de Kanban, filtrados pelo board slug."""
        config = self.get_board_config(slug)
        projetos = self.db.query(Projeto).all()
        return [
            self._format_card(p, config) for p in projetos
            if (p.kanban_dados or {}).get('_board_slug', 'fluxo-projetos') == slug
        ]

    def get_card(self, card_id: int) -> Optional[Dict[str, Any]]:
        """Retorna os detalhes de um único card com mapeamentos aplicados."""
        projeto = self.db.query(Projeto).filter_by(pipefy_id=card_id).first()
        if not projeto:
            return None
        config = self.get_board_config()
        return self._format_card(projeto, config)

    def _format_card(self, p: Projeto, config: Dict[str, Any]) -> Dict[str, Any]:
        """Formata um objeto Projeto para o formato de card do Kanban, aplicando mapeamentos inversos."""
        mappings = {}
        for fase in config.get('fases', []):
            for campo in fase.get('campos', []):
                if campo.get('mapeamento_coluna'):
                    mappings[campo['id']] = campo['mapeamento_coluna']

        dados = p.kanban_dados or {}
        # Sincronização Inversa: O valor da coluna real do banco prevalece
        for campo_id, coluna in mappings.items():
            val = getattr(p, coluna, None)
            if val is not None:
                if isinstance(val, (datetime, date)):
                    dados[campo_id] = val.isoformat()
                elif hasattr(val, '__float__'):
                    dados[campo_id] = float(val)
                else:
                    dados[campo_id] = val

        return {
            "card_id": p.pipefy_id,
            "titulo": p.nome,
            "fase_atual": p.fase_do_pipefy,
            "status": p.status,
            "dados": dados,
            "fee": float(p.fee) if p.fee else 0,
            "moeda": p.moeda
        }

    def create_card(self, slug: str, nome: str, dados_iniciais: Dict[str, Any], usuario_email: str) -> Projeto:
        """Cria um novo projeto/card no Kanban."""
        config = self.get_board_config(slug)
        fases = sorted(config['fases'], key=lambda x: x['ordem'])
        primeira_fase = fases[0]

        # Gerar pipefy_id único (Integer)
        while True:
            new_id = random.randint(100000000, 999999999)
            existing = self.db.query(Projeto).filter_by(pipefy_id=new_id).first()
            if not existing:
                break

        now = datetime.now()

        dados_iniciais['_board_slug'] = slug

        projeto = Projeto(
            pipefy_id=new_id,
            nome=nome,
            fase_do_pipefy=primeira_fase['nome'],
            status=primeira_fase.get('status_do_projeto', 'Ativo'),
            kanban_dados=dados_iniciais,
            data_de_inicio=now.date()
        )
        
        # Aplicar mapeamentos iniciais
        self._apply_column_mappings(projeto, config, dados_iniciais)
        
        self.db.add(projeto)
        self.db.flush()

        # Auditoria Imutável (com Labels para o Histórico)
        labels = {c['id']: c['label'] for c in primeira_fase.get('campos', [])}
        labels['titulo'] = 'Nome do Projeto'
        now = datetime.utcnow() - timedelta(hours=3)

        historico = KanbanHistorico(
            projeto_id=projeto.pipefy_id,
            usuario_email=usuario_email,
            data_evento=now,
            snapshot={
                "evento": "criacao",
                "fase_concluida": primeira_fase['nome'],
                "dados": dados_iniciais,
                "_labels": {c['id']: c['label'] for c in primeira_fase.get('campos', [])},
                "timestamp": now.isoformat()
            }
        )
        self.db.add(historico)
        self.db.commit()
        return projeto

    def move_card(self, projeto_id: int, nova_fase_id: str, dados_fase: Dict[str, Any], usuario_email: str) -> Projeto:
        """Move um card entre fases com validação determinística."""
        projeto = self.db.query(Projeto).filter_by(pipefy_id=projeto_id).first()
        if not projeto:
            raise ValueError("Projeto não encontrado.")

        config = self.get_board_config()
        fases = config['fases']
        fase_atual_nome = projeto.fase_do_pipefy
        
        target_fase = next((f for f in fases if f['id'] == nova_fase_id or f['nome'] == nova_fase_id), None)
        if not target_fase:
            raise ValueError(f"Fase destino '{nova_fase_id}' não encontrada.")

        current_fase = next((f for f in fases if f['nome'] == fase_atual_nome), None)

        # Regras de Transição Determinísticas
        if current_fase and current_fase['id'] != target_fase['id']:
            is_direct = target_fase.get('permite_acesso_direto', False)
            is_next = target_fase['ordem'] == current_fase['ordem'] + 1
            
            # Verificar se já visitou a fase anteriormente (retorno ao histórico)
            from sqlalchemy import or_
            already_visited = self.db.query(KanbanHistorico).filter(
                KanbanHistorico.projeto_id == projeto_id,
                or_(
                    KanbanHistorico.snapshot['fase'].astext == target_fase['nome'],
                    KanbanHistorico.snapshot['fase_concluida'].astext == target_fase['nome'],
                    KanbanHistorico.snapshot['fase_nova'].astext == target_fase['nome']
                )
            ).first() is not None

            # Verificar se a fase destino está na lista de fases permitidas configurada
            fases_permitidas = current_fase.get('fases_permitidas', [])
            is_in_permitidas = target_fase['id'] in fases_permitidas

            if not is_direct and not is_next and not already_visited and not is_in_permitidas:
                raise PhaseTransitionError(
                    f"Transição bloqueada: '{fase_atual_nome}' -> '{target_fase['nome']}' "
                    "viola a sequência definida."
                )

        now = datetime.utcnow() - timedelta(hours=3)
        
        # Atualiza dados dinâmicos (Merge NoSQL)
        current_dados = projeto.kanban_dados or {}
        current_dados.update(dados_fase)
        projeto.kanban_dados = current_dados
        
        # Aplicar mapeamentos de colunas (Sincronização Direta)
        self._apply_column_mappings(projeto, config, current_dados)
        
        # Atualiza Fase e Status
        projeto.fase_do_pipefy = target_fase['nome']
        
        # Sincroniza o status do projeto a partir da fase
        status_fase = target_fase.get('status_do_projeto')
        if status_fase:
            projeto.status = status_fase
        else:
            # Lógica de Status Base (Fallback)
            if target_fase['nome'].lower() in ['churn', 'cancelado', 'perdido']:
                projeto.status = 'Inativo'
            elif target_fase['nome'].lower() in ['inativo', 'pausado']:
                projeto.status = 'Inativo'
            else:
                projeto.status = 'Ativo'

        # Snapshot Imutável da fase que está sendo deixada
        historico = KanbanHistorico(
            projeto_id=projeto_id,
            usuario_email=usuario_email,
            data_evento=now,
            snapshot={
                "evento": "movimentacao",
                "fase_concluida": fase_atual_nome,
                "fase_nova": target_fase['nome'],
                "dados": dados_fase,
                "_labels": {c['id']: c['label'] for c in current_fase.get('campos', [])} if current_fase else {},
                "snapshot_completo": current_dados,
                "timestamp": now.isoformat()
            }
        )
        self.db.add(historico)
        self.db.commit()
        return projeto

    def update_card(self, projeto_id: int, nome: Optional[str], novos_dados: Dict[str, Any], usuario_email: str) -> Projeto:
        """Atualiza dados de um card e aplica mapeamentos de colunas."""
        projeto = self.db.query(Projeto).filter_by(pipefy_id=projeto_id).first()
        if not projeto:
            raise ValueError("Projeto não encontrado.")

        old_dados = {**projeto.kanban_dados} if projeto.kanban_dados else {}
        
        if nome:
            projeto.nome = nome

        current_dados = projeto.kanban_dados or {}
        current_dados.update(novos_dados)
        projeto.kanban_dados = current_dados

        config = self.get_board_config()
        self._apply_column_mappings(projeto, config, current_dados)
        
        # Identificar o que mudou para o log técnico
        changes = {}
        labels = {}
        for fase in config.get('fases', []):
            for campo in fase.get('campos', []):
                labels[campo['id']] = campo['label']

        for k, v in novos_dados.items():
            if old_dados.get(k) != v:
                changes[labels.get(k, k)] = {
                    "de": old_dados.get(k, "-"),
                    "para": v
                }

        if changes:
            now = datetime.utcnow() - timedelta(hours=3)
            historico = KanbanHistorico(
                projeto_id=projeto_id,
                usuario_email=usuario_email,
                data_evento=now,
                snapshot={
                    "evento": "atualizacao",
                    "fase_atual": projeto.fase_do_pipefy,
                    "alteracoes": changes,
                    "timestamp": now.isoformat()
                }
            )
            self.db.add(historico)

        self.db.commit()
        return projeto

    def update_config(self, slug: str, nova_config: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza a configuração do board (fases, campos, etc)."""
        fases = nova_config.get('fases', [])
        for i, fase in enumerate(fases):
            status = fase.get('status_do_projeto')
            if not status:
                raise ValueError(f"A fase '{fase.get('nome', f'Fase {i+1}')}' não possui um status de projeto definido.")
            if status not in ['Ativo', 'Onetime', 'Inativo']:
                raise ValueError(f"A fase '{fase.get('nome')}' possui um status de projeto inválido: '{status}'. Os valores permitidos são: Ativo, Onetime, Inativo.")

        stmt = select(KanbanConfig).where(KanbanConfig.slug == slug)
        result = self.db.execute(stmt).scalar_one_or_none()
        
        if not result:
            result = KanbanConfig(slug=slug)
            self.db.add(result)
            
        result.configuracao = nova_config
        self.db.commit()
        return nova_config

    def _apply_column_mappings(self, projeto: Projeto, config: Dict[str, Any], dados: Dict[str, Any]):
        """Aplica os valores do Kanban às colunas reais da tabela projetos baseado no config."""
        for fase in config.get('fases', []):
            for campo in fase.get('campos', []):
                coluna = campo.get('mapeamento_coluna')
                if coluna and coluna in self.mappable_columns:
                    val = dados.get(campo['id'])
                    if val is not None:
                        try:
                            # Conversão de tipos básica
                            if 'data' in coluna or 'date' in coluna:
                                if isinstance(val, str) and val:
                                    # Handle ISO strings for dates
                                    try:
                                        setattr(projeto, coluna, datetime.fromisoformat(val).date())
                                    except:
                                        setattr(projeto, coluna, datetime.strptime(val.split('T')[0], '%Y-%m-%d').date())
                            elif coluna == 'fee' or 'orcamento' in coluna:
                                if val == "":
                                    setattr(projeto, coluna, 0)
                                else:
                                    # Limpa possíveis formatações brasileiras se vier como string
                                    if isinstance(val, str):
                                        val = val.replace('.', '').replace(',', '.')
                                    setattr(projeto, coluna, float(val))
                            else:
                                setattr(projeto, coluna, val)
                            
                            # Mantém o JSONB sincronizado com o valor real para evitar divergência
                            projeto.kanban_dados[campo['id']] = val
                        except Exception as e:
                            print(f"Erro ao mapear coluna {coluna}: {e}")
        # Importante: Marcar como modificado para o SQLAlchemy detectar mudança profunda no dict JSONB
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(projeto, "kanban_dados")

    def clone_card_from_history(self, history_id: int, nome: str, usuario_email: str) -> Projeto:
        """Clona um card a partir de um snapshot do histórico, criando um novo card independente."""
        historico = self.db.query(KanbanHistorico).filter_by(id=history_id).first()
        if not historico:
            raise ValueError("Snapshot de histórico não encontrado.")

        snapshot = historico.snapshot
        fase_nome = snapshot.get("fase_concluida") or snapshot.get("fase_entrada")

        config = self.get_board_config()
        target_fase = next((f for f in config.get('fases', []) if f['nome'] == fase_nome), None)
        if not target_fase:
            raise ValueError(f"Fase '{fase_nome}' do snapshot não encontrada na configuração atual.")

        dados_iniciais = {
            **(snapshot.get("snapshot_completo") or {}),
            **(snapshot.get("dados_transicao") or {}),
            **(snapshot.get("dados") or {})
        }

        new_id = random.randint(100000000, 999999999)
        while self.db.query(Projeto).filter_by(pipefy_id=new_id).first():
            new_id = random.randint(100000000, 999999999)

        now_date = datetime.now()
        projeto = Projeto(
            pipefy_id=new_id,
            nome=nome,
            fase_do_pipefy=target_fase['nome'],
            status=target_fase.get('status_do_projeto', 'Ativo'),
            kanban_dados=dados_iniciais,
            data_de_inicio=now_date.date()
        )

        self._apply_column_mappings(projeto, config, dados_iniciais)
        self.db.add(projeto)
        self.db.flush()

        now_ts = datetime.utcnow() - timedelta(hours=3)
        clone_historico = KanbanHistorico(
            projeto_id=projeto.pipefy_id,
            usuario_email=usuario_email,
            data_evento=now_ts,
            snapshot={
                "evento": "criacao",
                "fase_concluida": target_fase['nome'],
                "dados": dados_iniciais,
                "_labels": snapshot.get("_labels", {}),
                "timestamp": now_ts.isoformat(),
                "clonado_de": {
                    "historico_id": history_id,
                    "projeto_original": historico.projeto_id,
                    "fase_original": fase_nome
                }
            }
        )
        self.db.add(clone_historico)
        self.db.commit()
        return projeto

    def list_boards(self) -> List[Dict[str, Any]]:
        """Lista todos os boards Kanban disponíveis."""
        configs = self.db.query(KanbanConfig).all()
        return [
            {
                "slug": c.slug,
                "nome": c.configuracao.get("nome", c.slug),
                "total_fases": len(c.configuracao.get("fases", []))
            }
            for c in configs
        ]

    def create_board(self, slug: str, nome: str) -> Dict[str, Any]:
        """Cria um novo board Kanban com configuração padrão."""
        existing = self.db.query(KanbanConfig).filter_by(slug=slug).first()
        if existing:
            raise ValueError(f"Já existe um board com o slug '{slug}'.")

        config = {
            "nome": nome,
            "fases": [
                {
                    "id": "fase_1",
                    "nome": "Pendente",
                    "ordem": 1,
                    "cor": "#95a5a6",
                    "status_do_projeto": "Ativo",
                    "fases_permitidas": [],
                    "campos": [
                        {"id": "responsavel", "label": "Responsável", "tipo": "string", "obrigatorio": False}
                    ]
                },
                {
                    "id": "fase_2",
                    "nome": "Em Andamento",
                    "ordem": 2,
                    "cor": "#3498db",
                    "status_do_projeto": "Ativo",
                    "fases_permitidas": [],
                    "campos": []
                },
                {
                    "id": "fase_3",
                    "nome": "Concluído",
                    "ordem": 3,
                    "cor": "#2ecc71",
                    "status_do_projeto": "Ativo",
                    "fases_permitidas": [],
                    "permite_acesso_direto": True,
                    "campos": [
                        {"id": "data_entrega", "label": "Data de Entrega", "tipo": "date", "obrigatorio": False}
                    ]
                }
            ]
        }

        new_config = KanbanConfig(slug=slug, configuracao=config)
        self.db.add(new_config)
        self.db.commit()
        return config

    def migrate_card_to_board(self, card_id: int, target_slug: str, usuario_email: str) -> Projeto:
        """Transfere um card para outro board."""
        projeto = self.db.query(Projeto).filter_by(pipefy_id=card_id).first()
        if not projeto:
            raise ValueError("Projeto não encontrado.")

        target_config = self.get_board_config(target_slug)
        if not target_config:
            raise ValueError(f"Board de destino '{target_slug}' não encontrado.")

        dados = projeto.kanban_dados or {}
        current_phase_name = projeto.fase_do_pipefy
        target_phase = next(
            (f for f in target_config.get('fases', []) if f['nome'] == current_phase_name),
            None
        )
        if not target_phase:
            fases = sorted(target_config.get('fases', []), key=lambda x: x['ordem'])
            target_phase = fases[0] if fases else None
            if not target_phase:
                raise ValueError("Board de destino não possui fases configuradas.")

        old_slug = dados.get('_board_slug', 'fluxo-projetos')
        dados['_board_slug'] = target_slug
        projeto.kanban_dados = dados
        projeto.fase_do_pipefy = target_phase['nome']
        projeto.status = target_phase.get('status_do_projeto', 'Ativo')

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(projeto, "kanban_dados")

        now_ts = datetime.utcnow() - timedelta(hours=3)
        historico = KanbanHistorico(
            projeto_id=card_id,
            usuario_email=usuario_email,
            data_evento=now_ts,
            snapshot={
                "evento": "migracao_board",
                "fase_concluida": current_phase_name,
                "fase_nova": target_phase['nome'],
                "board_origem": old_slug,
                "board_destino": target_slug,
                "dados": dados,
                "timestamp": now_ts.isoformat()
            }
        )
        self.db.add(historico)
        self.db.commit()
        return projeto

    def find_phase_by_token(self, token: str):
        """Busca a fase e o slug do board associados a um token de formulário público."""
        configs = self.db.query(KanbanConfig).all()
        for c in configs:
            config_data = c.configuracao
            for fase in config_data.get('fases', []):
                if fase.get('form_token') == token:
                    return c.slug, fase
        return None, None

    def create_card_in_phase(self, slug: str, fase: Dict[str, Any], nome: str, dados: Dict[str, Any], usuario_email: str) -> Projeto:
        """Cria um novo card diretamente em uma fase específica."""
        config = self.get_board_config(slug)

        new_id = random.randint(100000000, 999999999)
        while self.db.query(Projeto).filter_by(pipefy_id=new_id).first():
            new_id = random.randint(100000000, 999999999)

        now_date = datetime.now()
        dados['_board_slug'] = slug

        projeto = Projeto(
            pipefy_id=new_id,
            nome=nome,
            fase_do_pipefy=fase['nome'],
            status=fase.get('status_do_projeto', 'Ativo'),
            kanban_dados=dados,
            data_de_inicio=now_date.date()
        )

        self._apply_column_mappings(projeto, config, dados)
        self.db.add(projeto)
        self.db.flush()

        now_ts = datetime.utcnow() - timedelta(hours=3)
        historico = KanbanHistorico(
            projeto_id=projeto.pipefy_id,
            usuario_email=usuario_email,
            data_evento=now_ts,
            snapshot={
                "evento": "criacao",
                "fase_concluida": fase['nome'],
                "dados": dados,
                "_labels": {c['id']: c['label'] for c in fase.get('campos', [])},
                "timestamp": now_ts.isoformat()
            }
        )
        self.db.add(historico)
        self.db.commit()
        return projeto
