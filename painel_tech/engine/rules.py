SEVERIDADE_ORDEM = {"info": 1, "atencao": 2, "critico": 3}
SEVERIDADE_COR = {"info": "azul", "atencao": "ambar", "critico": "vermelho"}

INTERVENCAO_LABELS = {
    "intervencao": {"label": "Intervenção necessária", "emoji": "🚨", "cor": "vermelho"},
    "atencao": {"label": "Atenção", "emoji": "⚠️", "cor": "ambar"},
    "normal": {"label": "Normal", "emoji": "✅", "cor": "verde"},
}


def _match(spec, valor):
    if valor is None:
        return False
    if isinstance(spec, dict):
        if "in" in spec and valor not in spec["in"]:
            return False
        if "min" in spec and not (valor >= spec["min"]):
            return False
        if "max" in spec and not (valor <= spec["max"]):
            return False
        return True
    return valor == spec


def _match_quando(quando, ctx):
    for campo, spec in quando.items():
        if not _match(spec, ctx.get(campo)):
            return False
    return True


def avaliar_regras(ctx, cfg):
    alertas = []
    for regra in cfg["regras"]:
        if _match_quando(regra.get("quando", {}), ctx):
            alerta = dict(regra)
            alerta["cor"] = SEVERIDADE_COR.get(regra.get("severidade", "info"), "cinza")
            alertas.append(alerta)
    return alertas


def calcular_intervencao(alertas):
    if not alertas:
        return {"nivel": "normal", **INTERVENCAO_LABELS["normal"], "motivo": None}
    prioridade_sev = max(
        SEVERIDADE_ORDEM.get(a.get("severidade", "info"), 1) for a in alertas
    )
    if prioridade_sev >= SEVERIDADE_ORDEM["critico"]:
        nivel = "intervencao"
    elif prioridade_sev >= SEVERIDADE_ORDEM["atencao"]:
        nivel = "atencao"
    else:
        nivel = "normal"
    destaque = max(
        alertas, key=lambda a: SEVERIDADE_ORDEM.get(a.get("severidade", "info"), 1)
    )
    return {
        "nivel": nivel,
        **INTERVENCAO_LABELS[nivel],
        "motivo": destaque.get("mensagem"),
    }
