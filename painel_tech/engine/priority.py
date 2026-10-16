from ..domain import nivel_indicador

PRIORIDADE_LABELS = {
    "critica": {"label": "Crítica", "emoji": "🔴"},
    "alta": {"label": "Alta", "emoji": "🔥"},
    "media": {"label": "Média", "emoji": "🟡"},
    "baixa": {"label": "Baixa", "emoji": "⚪"},
}


def classificar(score, bandas):
    if score >= bandas["critica"]:
        return "critica"
    if score >= bandas["alta"]:
        return "alta"
    if score >= bandas["media"]:
        return "media"
    return "baixa"


def calcular_prioridade(projeto, cfg):
    pesos = cfg["prioridade"]["pesos"]
    impacto = nivel_indicador("impacto", projeto["impacto"])
    urgencia = nivel_indicador("urgencia", projeto["urgencia"])
    risco = nivel_indicador("risco", projeto["risco"])
    esforco = nivel_indicador("esforco", projeto["esforco"])

    bruto = (
        pesos["impacto"] * impacto
        + pesos["urgencia"] * urgencia
        + pesos["risco"] * risco
        + pesos["esforco"] * (5 - esforco)
    )
    soma_pesos = sum(pesos.values()) or 1
    score = bruto / soma_pesos
    indice = round((score - 1) / 3 * 100)
    nivel = classificar(score, cfg["prioridade"]["bandas"])
    return {
        "score": round(score, 2),
        "indice": indice,
        "nivel": nivel,
        "label": PRIORIDADE_LABELS[nivel]["label"],
        "emoji": PRIORIDADE_LABELS[nivel]["emoji"],
    }
