from sqlalchemy.orm import Session
from models import InvestidorProjeto, ProjetoAtivo, ProjetoOnetime

class OperacaoService:
    @staticmethod
    def get_projetos_operacao(db: Session, email: str, squad: str) -> list:
        """
        Retorna todos os projetos vinculados e ativos ao usuário para a tela de operação.
        Considera Projetos Ativos, Onetime e Inativos.
        """
        todas_tabelas = [ProjetoAtivo, ProjetoOnetime]
        meus_projetos_dict = {}

        if squad == "Gerência":
            # Para gerência, buscar de todas as tabelas
            for model in todas_tabelas:
                projetos = db.query(model).all()
                for p in projetos:
                    if p.pipefy_id not in meus_projetos_dict:
                        meus_projetos_dict[p.pipefy_id] = p
        else:
            # Busca vínculos ativos do investidor
            vinculos = db.query(InvestidorProjeto).filter(
                InvestidorProjeto.email_investidor == email,
                InvestidorProjeto.active == True
            ).all()
            
            # Extrai os IDs dos projetos vinculados
            ids_vinculados = [v.pipefy_id_projeto for v in vinculos]
            
            if ids_vinculados:
                for model in todas_tabelas:
                    projetos = db.query(model).filter(model.pipefy_id.in_(ids_vinculados)).all()
                    for p in projetos:
                        if p.pipefy_id not in meus_projetos_dict:
                            meus_projetos_dict[p.pipefy_id] = p

        # Prepara a lista a ser retornada compatível com _projeto_to_dict em app.py
        # Como _projeto_to_dict é definido em app.py, nós retornamos os objetos models em si,
        # ou construímos os dicionários aqui mesmo. Para isolar bem, vamos construir aqui.
        meus_projetos = []
        for p in meus_projetos_dict.values():
            meus_projetos.append({
                "id": p.pipefy_id,
                "pipefy_id": p.pipefy_id,
                "nome": p.nome,
                "documento": getattr(p, "documento", ""),
                "fee": getattr(p, "fee", 0),
                "moeda": getattr(p, "moeda", ""),
                "squad_atribuida": getattr(p, "squad_atribuida", ""),
                "produto_contratado": getattr(p, "produto_contratado", ""),
                "data_de_inicio": p.data_de_inicio.isoformat() if getattr(p, "data_de_inicio", None) else None,
                "cohort": getattr(p, "cohort", ""),
                "meta_account_id": getattr(p, "meta_account_id", ""),
                "google_account_id": getattr(p, "google_account_id", ""),
                "fase_do_pipefy": getattr(p, "fase_do_pipefy", ""),
                "step": getattr(p, "step", ""),
                "informacoes_gerais": getattr(p, "informacoes_gerais", ""),
                "orcamento_midia_meta": getattr(p, "orcamento_midia_meta", 0),
                "orcamento_midia_google": getattr(p, "orcamento_midia_google", 0),
                "data_fim": p.data_fim.isoformat() if getattr(p, "data_fim", None) else None,
                "ekyte_workspace": getattr(p, "ekyte_workspace", ""),
            })

        return meus_projetos
