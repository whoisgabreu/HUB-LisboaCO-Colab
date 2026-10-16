from flask import abort, render_template, request, url_for

from .. import bp, db, view_utils
from ..config import get_config


def _linhas_filtradas(cfg):
    linhas = view_utils.construir_linhas(db.projetos_com_etapas(), cfg)
    return linhas, view_utils.aplicar_filtros(linhas, request.args)


@bp.route("/")
def dashboard():
    cfg = get_config()
    linhas, filtradas = _linhas_filtradas(cfg)
    atencao = view_utils.ordenar_prioridade(
        [
            linha
            for linha in filtradas
            if linha["analise"]["intervencao"]["nivel"] != "normal"
        ]
    )
    membros = db.listar_membros()
    return render_template(
        "painel_tech/dashboard.html",
        contagem=view_utils.contagem_por_status(filtradas),
        atencao=atencao,
        linhas=view_utils.ordenar_prioridade(filtradas),
        membros=membros,
        chips=view_utils.chips_filtros(request.args, membros, "painel_tech.dashboard"),
        url_limpar=url_for("painel_tech.dashboard"),
        args=request.args,
    )


@bp.route("/capacidade")
def capacidade_pagina():
    cfg = get_config()
    linhas = view_utils.construir_linhas(db.projetos_com_etapas(), cfg)
    membros = db.listar_membros()
    return render_template(
        "painel_tech/capacidade.html",
        capacidade=view_utils.capacidade_membros(linhas, membros, cfg),
    )


@bp.route("/capacidade/<int:membro_id>")
def capacidade_membro(membro_id):
    membros = db.listar_membros()
    membro = next((m for m in membros if m["id"] == membro_id), None)
    if not membro:
        abort(404)
    cfg = get_config()
    linhas = view_utils.construir_linhas(db.projetos_com_etapas(), cfg)
    do_membro = [
        linha
        for linha in linhas
        if linha["projeto"].get("responsavel_id") == membro_id
    ]
    capacidades = {
        cap["id"]: cap
        for cap in view_utils.capacidade_membros(linhas, membros, cfg)
    }
    return render_template(
        "painel_tech/capacidade_membro.html",
        membro=membro,
        cap=capacidades.get(membro_id),
        linhas=view_utils.ordenar_prioridade(do_membro),
    )


@bp.route("/metricas")
def metricas_pagina():
    cfg = get_config()
    linhas, filtradas = _linhas_filtradas(cfg)
    ativos = view_utils.ordenar_prioridade(
        [linha for linha in filtradas if linha["projeto"]["status"] == "ativo"]
    )
    membros = db.listar_membros()
    return render_template(
        "painel_tech/metricas.html",
        contagem=view_utils.contagem_por_status(filtradas),
        ativos=ativos,
        tendencia=view_utils.tendencia_mensal(filtradas, 6),
        membros=membros,
        chips=view_utils.chips_filtros(request.args, membros, "painel_tech.metricas_pagina"),
        url_limpar=url_for("painel_tech.metricas_pagina"),
        args=request.args,
    )