from datetime import date, datetime

from . import domain


def data_br(valor):
    if not valor:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    texto = str(valor)
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return texto


def tempo_br(segundos):
    if not segundos:
        return "—"
    segundos = max(0, int(segundos))
    horas, resto = divmod(segundos, 3600)
    minutos = resto // 60
    if horas:
        return f"{horas}h {minutos:02d}min"
    return f"{minutos}min"


def duracao_br(valor):
    if valor is None:
        return "—"
    total = int(valor.total_seconds())
    horas = total // 3600
    minutos = (total % 3600) // 60
    segundos = total % 60
    if horas:
        return f"{horas}h {minutos:02d}min"
    if minutos:
        return f"{minutos}min {segundos:02d}s"
    return f"{segundos}s"


def minutos_br(valor):
    if valor is None:
        return "—"
    total = max(0, int(valor))
    horas, minutos = divmod(total, 60)
    if horas and minutos:
        return f"{horas}h {minutos:02d}min"
    if horas:
        return f"{horas}h"
    return f"{minutos}min"


def registrar(app):
    app.jinja_env.filters["data_br"] = data_br
    app.jinja_env.filters["tempo_br"] = tempo_br
    app.jinja_env.filters["duracao_br"] = duracao_br
    app.jinja_env.filters["minutos_br"] = minutos_br

    def obter_notificacoes():
        from . import notificacoes

        return notificacoes.resumo()

    @app.context_processor
    def injetar_globais():
        from flask import request

        if not (request.endpoint or "").startswith("painel_tech."):
            return {}
        return {
            "notificacoes": obter_notificacoes(),
            "STATUS": domain.STATUS,
            "PRIORIDADE": domain.PRIORIDADE,
            "RITMO": domain.RITMO,
            "INTERVENCAO": domain.INTERVENCAO,
            "ETAPA_STATUS": domain.ETAPA_STATUS,
            "INDICADORES": domain.INDICADORES,
            "status_meta": domain.label_status,
            "prioridade_meta": domain.label_prioridade,
            "ritmo_meta": domain.label_ritmo,
            "intervencao_meta": domain.label_intervencao,
            "etapa_status_meta": domain.label_etapa_status,
            "indicador_meta": domain.meta_indicador,
            "opcoes": domain.opcoes,
        }
