from . import db, view_utils
from .config import get_config


def resumo():
    from flask import g

    cache = getattr(g, "notificacoes_cache", None)
    if cache is not None:
        return cache

    if view_utils.quer_fragmento():
        g.notificacoes_cache = []
        return g.notificacoes_cache

    config = get_config()
    linhas = view_utils.construir_linhas(db.projetos_com_etapas(), config)
    itens = []
    for linha in linhas:
        analise = linha["analise"]
        if analise["intervencao"]["nivel"] != "normal":
            itens.append(
                {
                    "projeto_id": linha["projeto"]["id"],
                    "nome": linha["projeto"]["nome"],
                    "motivo": analise["intervencao"]["motivo"],
                    "cor": analise["intervencao"]["cor"],
                    "label": analise["intervencao"]["label"],
                }
            )

    membros = db.listar_membros()
    for cap in view_utils.capacidade_membros(linhas, membros, config):
        if cap["situacao"] in ("cheio", "acima"):
            itens.append(
                {
                    "projeto_id": None,
                    "url": f"/projetos?responsavel={cap['id']}&status=ativo",
                    "nome": cap["nome"],
                    "motivo": f"Capacidade {cap['ativos']}/{cap['limite']}",
                    "cor": cap["cor"],
                    "label": cap["rotulo"],
                }
            )

    itens.sort(key=lambda item: item["nome"].lower())
    g.notificacoes_cache = itens
    return itens