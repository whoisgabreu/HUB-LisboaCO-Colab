from datetime import date, datetime, timedelta

from flask import render_template, request, url_for

from .. import bp, db, view_utils
from .. import planejador
from ..config import get_config


def _parse_data(valor):
    if not valor:
        return None
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _url_semana(segunda, args):
    parametros = {
        chave: valor
        for chave, valor in args.items()
        if chave not in ("semana",)
    }
    parametros["semana"] = segunda.isoformat()
    return url_for("painel_tech.agenda_pagina", **parametros)


@bp.route("/agenda")
def agenda_pagina():
    cfg = get_config()
    quando = _parse_data(request.args.get("semana")) or date.today()
    linhas = view_utils.construir_linhas(db.projetos_com_etapas(), cfg)
    filtradas = view_utils.aplicar_filtros(linhas, request.args)
    agenda = planejador.planejar_semana(filtradas, cfg, quando)
    membros = db.listar_membros()
    segunda = agenda["semana_inicio"]
    hoje = date.today()
    contexto = {
        "agenda": agenda,
        "membros": membros,
        "hoje": hoje,
        "chips": view_utils.chips_filtros(
            request.args, membros, "painel_tech.agenda_pagina"
        ),
        "url_limpar": url_for("painel_tech.agenda_pagina"),
        "args": request.args,
        "url_anterior": _url_semana(segunda - timedelta(days=7), request.args),
        "url_proxima": _url_semana(segunda + timedelta(days=7), request.args),
        "url_hoje": _url_semana(hoje - timedelta(days=hoje.weekday()), request.args),
    }
    if view_utils.quer_fragmento():
        return render_template("painel_tech/partials/_agenda_grelha.html", **contexto)
    return render_template("painel_tech/agenda.html", **contexto)
