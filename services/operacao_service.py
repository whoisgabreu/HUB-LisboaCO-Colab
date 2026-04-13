from projetos.models import InvestidorProjeto, ProjetoAtivo, ProjetoOnetime

class OperacaoService:
    @staticmethod
    def get_projetos_operacao(email: str, squad: str) -> list:
        """
        Retorna todos os projetos vinculados e ativos ao usuário para a tela de operação.
        Migrado para Django ORM.
        """
        todas_tabelas = [ProjetoAtivo, ProjetoOnetime]
        meus_projetos_dict = {}

        if squad == "Gerência":
            for model in todas_tabelas:
                projetos = model.objects.all()
                for p in projetos:
                    if p.pipefy_id not in meus_projetos_dict:
                        meus_projetos_dict[p.pipefy_id] = p
        else:
            ids_vinculados = InvestidorProjeto.objects.filter(
                email_investidor=email,
                active=True
            ).values_list('pipefy_id_projeto', flat=True)
            
            if ids_vinculados:
                for model in todas_tabelas:
                    projetos = model.objects.filter(pipefy_id__in=ids_vinculados)
                    for p in projetos:
                        if p.pipefy_id not in meus_projetos_dict:
                            meus_projetos_dict[p.pipefy_id] = p

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
                "data_de_inicio": p.data_de_inicio.isoformat() if p.data_de_inicio else None,
                "cohort": getattr(p, "cohort", ""),
                "meta_account_id": getattr(p, "meta_account_id", ""),
                "google_account_id": getattr(p, "google_account_id", ""),
                "fase_do_pipefy": getattr(p, "fase_do_pipefy", ""),
                "step": getattr(p, "step", ""),
                "informacoes_gerais": getattr(p, "informacoes_gerais", ""),
                "orcamento_midia_meta": getattr(p, "orcamento_midia_meta", 0),
                "orcamento_midia_google": getattr(p, "orcamento_midia_google", 0),
                "data_fim": p.data_fim.isoformat() if p.data_fim else None,
                "ekyte_workspace": getattr(p, "ekyte_workspace", ""),
            })

        return meus_projetos
