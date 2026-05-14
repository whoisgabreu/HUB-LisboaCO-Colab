import random
from datetime import datetime
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
                    "campos": [
                        {"id": "prioridade", "label": "Prioridade", "tipo": "select", "opcoes": ["Baixa", "Média", "Alta"]}
                    ]
                },
                {
                    "id": "concluido",
                    "nome": "Concluído",
                    "ordem": 3,
                    "cor": "#2ecc71",
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
        """Lista todos os projetos formatados como cards de Kanban."""
        projetos = self.db.query(Projeto).all()
        cards = []
        for p in projetos:
            cards.append({
                "card_id": p.pipefy_id,
                "titulo": p.nome,
                "fase_atual": p.fase_do_pipefy,
                "status": p.status,
                "dados": p.kanban_dados or {},
                "fee": float(p.fee) if p.fee else 0,
                "moeda": p.moeda
            })
        return cards

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

        projeto = Projeto(
            pipefy_id=new_id,
            nome=nome,
            fase_do_pipefy=primeira_fase['nome'],
            status='Ativo',
            kanban_dados=dados_iniciais,
            data_de_inicio=now.date()
        )
        
        self.db.add(projeto)
        self.db.flush()

        # Auditoria Imutável
        historico = KanbanHistorico(
            projeto_id=projeto.pipefy_id,
            usuario_email=usuario_email,
            snapshot={
                "evento": "criacao",
                "fase": primeira_fase['nome'],
                "dados": dados_iniciais,
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
            already_visited = self.db.query(KanbanHistorico).filter(
                KanbanHistorico.projeto_id == projeto_id,
                KanbanHistorico.snapshot['fase'].astext == target_fase['nome']
            ).first() is not None

            if not is_direct and not is_next and not already_visited:
                raise PhaseTransitionError(
                    f"Transição bloqueada: '{fase_atual_nome}' -> '{target_fase['nome']}' "
                    "viola a sequência definida."
                )

        now = datetime.now()
        
        # Atualiza dados dinâmicos (Merge NoSQL)
        current_dados = projeto.kanban_dados or {}
        current_dados.update(dados_fase)
        projeto.kanban_dados = current_dados
        
        # Atualiza Fase e Status
        projeto.fase_do_pipefy = target_fase['nome']
        
        # Lógica de Status Base
        if target_fase['nome'].lower() in ['churn', 'cancelado', 'perdido']:
            projeto.status = 'Churn'
        elif target_fase['nome'].lower() in ['inativo', 'pausado']:
            projeto.status = 'Inativo'
        else:
            projeto.status = 'Ativo'

        # Snapshot Imutável
        historico = KanbanHistorico(
            projeto_id=projeto_id,
            usuario_email=usuario_email,
            snapshot={
                "evento": "movimentacao",
                "fase_anterior": fase_atual_nome,
                "fase_nova": target_fase['nome'],
                "dados_transicao": dados_fase,
                "snapshot_completo": current_dados,
                "timestamp": now.isoformat()
            }
        )
        self.db.add(historico)
        self.db.commit()
        return projeto

    def update_config(self, slug: str, nova_config: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza a configuração do board (fases, campos, etc)."""
        stmt = select(KanbanConfig).where(KanbanConfig.slug == slug)
        result = self.db.execute(stmt).scalar_one_or_none()
        
        if not result:
            result = KanbanConfig(slug=slug)
            self.db.add(result)
            
        result.configuracao = nova_config
        self.db.commit()
        return nova_config
