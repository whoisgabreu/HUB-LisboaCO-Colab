from services import ekyte_service
from services import google_agenda_service

FONTES_DISPONIVEIS = ("ekyte", "google")
JANELA_AGENDA_DIAS = 7


def _item_ekyte(t: dict) -> dict:
    return {
        "fonte": "ekyte",
        "tipo": "tarefa",
        "titulo": t.get("titulo") or "Tarefa sem título",
        "data": t.get("prazo") or "",
        "rotulo": t.get("fase") or "",
        "sub": t.get("workspace") or "",
        "link": t.get("url") or "",
        "inicio": "",
        "fim": "",
        "dia_todo": False,
    }


def _item_google(e: dict) -> dict:
    inicio = e.get("inicio") or ""
    return {
        "fonte": "google",
        "tipo": "evento",
        "titulo": e.get("titulo") or "(sem título)",
        "data": inicio[:10] if "T" in inicio else inicio,
        "rotulo": inicio,        # data/hora completa (o front formata)
        "sub": e.get("local") or "",
        "link": e.get("link") or "",
        "inicio": inicio,
        "fim": e.get("fim") or "",
        "dia_todo": bool(inicio) and "T" not in inicio,
    }


def _provedor_google(email: str, dias: int = JANELA_AGENDA_DIAS) -> tuple:
    res = google_agenda_service.listar_eventos(email, dias=dias)
    if not res.get("conectado"):
        return [], {"conectado": False, "total": 0, "erro": res.get("erro")}
    eventos = res.get("eventos") or []
    return [_item_google(e) for e in eventos], {"conectado": True, "total": len(eventos)}


def listar_itens(email: str, fontes=None, limite: int = None) -> dict:
    """Agrega itens de múltiplas fontes (ekyte e google), ordenados por data.

    Cada item: {fonte, tipo, titulo, data, rotulo, sub, link, inicio}
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
        google_itens, google_info = _provedor_google(email)
        info["google"] = google_info
        itens += google_itens

    def chave(it):
        ref = it.get("inicio") or (it["data"] + "T00:00:00" if it.get("data") else "")
        return (0, ref) if ref else (1, "9999-12-31")

    itens.sort(key=chave)
    total = len(itens)
    if limite and limite > 0:
        itens = itens[:limite]

    out = {"itens": itens, "total": total, "fontes": info}
    if atualizando:
        out["atualizando"] = True
    return out


def _eventos_hoje(eventos) -> int:
    """Conta eventos que ocorrem hoje (intervalo sobrepõe o dia de hoje, em America/Sao_Paulo)."""
    from datetime import datetime, time, timedelta
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Sao_Paulo")
    except Exception:
        tz = None
    hoje = datetime.now(tz).date() if tz else datetime.now().date()
    d0 = datetime.combine(hoje, time.min)
    d1 = datetime.combine(hoje + timedelta(days=1), time.min)
    count = 0
    for e in eventos:
        ini_raw = e.get("inicio")
        fim_raw = e.get("fim") or ini_raw
        try:
            if ini_raw and "T" in ini_raw:
                ini = datetime.fromisoformat(ini_raw)
            elif ini_raw:
                ini = datetime.fromisoformat(ini_raw + "T00:00:00")
            else:
                continue
            fim = datetime.fromisoformat(fim_raw) if fim_raw and "T" in fim_raw else (datetime.fromisoformat(fim_raw + "T23:59:59") if fim_raw else ini)
        except Exception:
            continue
        if ini.tzinfo is not None:
            ini = ini.astimezone(tz)
        if fim.tzinfo is not None:
            fim = fim.astimezone(tz)
        ini = ini.replace(tzinfo=None)
        fim = fim.replace(tzinfo=None)
        if (ini < d1) and (fim > d0):
            count += 1
    return count


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

    res = google_agenda_service.listar_eventos(email, dias=JANELA_AGENDA_DIAS)
    google_conectado = bool(res.get("conectado"))
    proxima = None
    if google_conectado:
        eventos = res.get("eventos") or []
        agenda_hoje = _eventos_hoje(eventos)
        proxima = _proxima_reuniao(eventos)

    out = {
        "tarefas_total": tarefas_total,
        "agenda_hoje": agenda_hoje,
        "google_conectado": google_conectado,
        "proxima_reuniao": proxima,
    }
    if atualizando:
        out["atualizando"] = True
    return out


def _proxima_reuniao(eventos):
    """Próximo evento com horário cujo início seja >= agora (America/Sao_Paulo)."""
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Sao_Paulo")
    except Exception:
        tz = None
    agora = datetime.now(tz) if tz else datetime.now()
    melhor = None
    for e in eventos:
        ini = e.get("inicio")
        if not ini or "T" not in ini:
            continue
        try:
            ini_dt = datetime.fromisoformat(ini)
        except Exception:
            continue
        if ini_dt.tzinfo is None and tz is not None:
            ini_dt = ini_dt.replace(tzinfo=tz)
        if tz is not None:
            ini_dt = ini_dt.astimezone(tz)
        if ini_dt >= agora and (melhor is None or ini_dt < melhor[0]):
            melhor = (ini_dt, e)
    if not melhor:
        return None
    return {"titulo": melhor[1].get("titulo") or "", "inicio": melhor[1].get("inicio") or ""}