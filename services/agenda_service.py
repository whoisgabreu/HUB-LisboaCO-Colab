from services import ekyte_service

FONTES_DISPONIVEIS = ("ekyte", "google")


def _item_ekyte(t: dict) -> dict:
    return {
        "fonte": "ekyte",
        "tipo": "tarefa",
        "titulo": t.get("titulo") or "Tarefa sem título",
        "data": t.get("prazo") or "",
        "rotulo": t.get("fase") or "",
        "sub": t.get("workspace") or "",
        "link": t.get("url") or "",
    }


def _provedor_google() -> tuple:
    """Placeholder para o vínculo futuro com Google Agenda (eventos)."""
    return [], {"conectado": False, "total": 0}


def listar_itens(email: str, fontes=None, limite: int = None) -> dict:
    """Agrega itens de múltiplas fontes (ekyte hoje; google futura), ordenados por data.

    Cada item: {fonte, tipo, titulo, data, rotulo, sub, link}
    Retorno: {itens, total, fontes:{<fonte>: {info}}}
    """
    if not fontes:
        fontes = ["ekyte"]
    elif isinstance(fontes, str):
        fontes = [f.strip().lower() for f in fontes.split(",") if f.strip()]

    itens = []
    info = {}
    atualizando = False

    if "ekyte" in fontes:
        dados = ekyte_service.listar_tarefas_do_email(email, limite=None)
        lista = dados.get("tarefas") or [] if isinstance(dados, dict) else []
        info["ekyte"] = {
            "total": dados.get("total") or len(lista),
            "configurado": "erro" not in dados,
            "erro": dados.get("erro"),
        }
        if dados.get("atualizando"):
            atualizando = True
        itens += [_item_ekyte(t) for t in lista]

    if "google" in fontes:
        google_itens, google_info = _provedor_google()
        info["google"] = google_info
        itens += google_itens

    def chave(it):
        return (0, it["data"][:10]) if it.get("data") else (1, "9999-12-31")

    itens.sort(key=chave)
    total = len(itens)
    if limite and limite > 0:
        itens = itens[:limite]

    out = {"itens": itens, "total": total, "fontes": info}
    if atualizando:
        out["atualizando"] = True
    return out


def resumo(email: str) -> dict:
    """Contadores leves para o widget: tarefas em aberto + eventos de hoje."""
    tarefas_total = 0
    agenda_hoje = 0
    google_conectado = False
    atualizando = False

    dados = ekyte_service.listar_tarefas_do_email(email, limite=None)
    if isinstance(dados, dict):
        if dados.get("atualizando"):
            atualizando = True
        if "erro" not in dados:
            tarefas_total = dados.get("total") or len(dados.get("tarefas") or [])

    if "google" in FONTES_DISPONIVEIS:
        _g, g_info = _provedor_google()
        google_conectado = bool(g_info.get("conectado"))
        agenda_hoje = g_info.get("total") or 0

    out = {
        "tarefas_total": tarefas_total,
        "agenda_hoje": agenda_hoje,
        "google_conectado": google_conectado,
    }
    if atualizando:
        out["atualizando"] = True
    return out