from datetime import date, datetime, timedelta

from flask import Response, render_template, request, url_for

from .. import bp, view_utils
from .. import relatorios as rel
from ..config import get_config

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DIAS_PADRAO = 30
POR_PAGINA_PADRAO = 25


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


def _periodo(args):
    hoje = date.today()
    de = _parse_data(args.get("de")) or (hoje - timedelta(days=DIAS_PADRAO))
    ate = _parse_data(args.get("ate")) or hoje
    if de > ate:
        de, ate = ate, de
    return de, ate


def _int_arg(args, nome, padrao, opcoes=None):
    try:
        valor = int(args.get(nome))
    except (TypeError, ValueError):
        return padrao
    if opcoes and valor not in opcoes:
        return padrao
    return valor


def _aba(args):
    aba = args.get("aba", "resumo")
    return aba if aba in rel.SECOES else "resumo"


def _parametros_export(args, de, ate):
    parametros = dict(args)
    parametros["de"] = de.isoformat()
    parametros["ate"] = ate.isoformat()
    for chave in ("aba", "pagina", "por_pagina"):
        parametros.pop(chave, None)
    return parametros


@bp.route("/relatorios")
def relatorios_pagina():
    de_data, ate_data = _periodo(request.args)
    de, ate = rel.intervalo(de_data, ate_data)
    aba = _aba(request.args)
    por_pagina = _int_arg(
        request.args, "por_pagina", POR_PAGINA_PADRAO, rel.POR_PAGINA_OPCOES
    )
    pagina = _int_arg(request.args, "pagina", 1)
    relatorio = rel.construir_relatorio(de, ate, request.args, get_config())
    secao = rel.preparar_secao(relatorio, aba, pagina, por_pagina)
    contexto = {
        "relatorio": relatorio,
        "secao": secao,
        "aba": aba,
        "por_pagina": por_pagina,
        "por_pagina_opcoes": rel.POR_PAGINA_OPCOES,
        "de_data": de_data,
        "ate_data": ate_data,
        "parametros_base": {
            "de": de_data.isoformat(),
            "ate": ate_data.isoformat(),
            "aba": aba,
            "por_pagina": por_pagina,
        },
        "url_export": url_for(
            "painel_tech.relatorios_export",
            **_parametros_export(request.args, de_data, ate_data),
        ),
    }
    if view_utils.quer_fragmento():
        return render_template("painel_tech/partials/_relatorio_secao.html", **contexto)
    return render_template("painel_tech/relatorios.html", **contexto)


@bp.route("/relatorios/export.xlsx")
def relatorios_export():
    de_data, ate_data = _periodo(request.args)
    de, ate = rel.intervalo(de_data, ate_data)
    relatorio = rel.construir_relatorio(de, ate, request.args, get_config())
    buffer = rel.gerar_xlsx(relatorio)
    nome = f"relatorio_tech_{de_data.isoformat()}_a_{ate_data.isoformat()}.xlsx"
    return Response(
        buffer.getvalue(),
        content_type=XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
