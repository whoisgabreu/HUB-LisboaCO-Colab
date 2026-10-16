import os
import time
import requests
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

from sqlalchemy import text

from database import Session

TOKEN_URL = "https://oauth2.googleapis.com/token"
EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
TZ = ZoneInfo("America/Sao_Paulo")
ACCESS_TTL = 3300      # ~55 min (access token do Google dura 1h)
EVENTOS_TTL = 300      # cache de eventos por 5 min

_access_cache = {}
_eventos_cache = {}


def _client():
    return os.getenv("GOOGLE_CLIENT_ID"), os.getenv("GOOGLE_CLIENT_SECRET")


def salvar_token(db, email, refresh_token, scope):
    db.execute(text(
        "INSERT INTO plataforma_geral.usuario_google_token (email, refresh_token, scope, atualizado_em) "
        "VALUES (:e, :r, :s, now()) "
        "ON CONFLICT (email) DO UPDATE SET refresh_token=EXCLUDED.refresh_token, "
        "scope=EXCLUDED.scope, atualizado_em=now()"
    ), {"e": email, "r": refresh_token, "s": scope or ""})
    db.commit()
    _access_cache.pop(email, None)
    _eventos_cache.pop(email, None)


def token_do_email(db, email):
    row = db.execute(text(
        "SELECT refresh_token, scope FROM plataforma_geral.usuario_google_token WHERE email=:e"
    ), {"e": email}).mappings().first()
    return dict(row) if row else None


def desconectar(db, email):
    db.execute(text("DELETE FROM plataforma_geral.usuario_google_token WHERE email=:e"), {"e": email})
    db.commit()
    _access_cache.pop(email, None)
    _eventos_cache.pop(email, None)


def _access_token(email, refresh_token):
    now = time.time()
    c = _access_cache.get(email)
    if c and c["exp"] > now:
        return c["token"], None
    cid, csec = _client()
    try:
        r = requests.post(TOKEN_URL, data={
            "client_id": cid,
            "client_secret": csec,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }, timeout=15)
    except Exception as e:
        return None, {"erro": "rede", "detalhe": str(e)}
    d = r.json() if r.content else {}
    if r.status_code != 200 or "access_token" not in d:
        return None, d
    _access_cache[email] = {"token": d["access_token"], "exp": now + ACCESS_TTL}
    return d["access_token"], None


def listar_eventos(email, dias=7, forcar=False):
    """Eventos do calendário principal (hoje + próximos `dias`), normalizados."""
    with Session() as db:
        tok = token_do_email(db, email)
    if not tok or not tok.get("refresh_token"):
        return {"conectado": False, "eventos": []}

    now = time.time()
    cache = _eventos_cache.get(email)
    if cache and not forcar and (now - cache["ts"]) < EVENTOS_TTL:
        return cache["data"]

    access, err = _access_token(email, tok["refresh_token"])
    if not access:
        # token inválido/revogado
        return {"conectado": False, "eventos": [], "erro": "token", "detalhe": err}

    hoje = datetime.now(TZ)
    inicio = datetime.combine(hoje.date(), dtime.min, tzinfo=TZ)
    fim = datetime.combine((hoje + timedelta(days=dias)).date(), dtime.max, tzinfo=TZ)
    try:
        r = requests.get(EVENTS_URL, params={
            "timeMin": inicio.isoformat(),
            "timeMax": fim.isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 250,
        }, headers={"Authorization": f"Bearer {access}"}, timeout=15)
    except Exception as e:
        return {"conectado": True, "eventos": [], "erro": "rede", "detalhe": str(e)}

    d = r.json() if r.content else {}
    if r.status_code != 200:
        return {"conectado": True, "eventos": [], "erro": "api", "detalhe": d}

    eventos = []
    for e in (d.get("items") or []):
        ini = e.get("start") or {}
        f = e.get("end") or {}
        eventos.append({
            "id": e.get("id"),
            "titulo": e.get("summary") or "(sem título)",
            "inicio": ini.get("dateTime") or ini.get("date"),
            "fim": f.get("dateTime") or f.get("date"),
            "local": e.get("location") or "",
            "link": e.get("htmlLink") or "",
        })

    out = {"conectado": True, "eventos": eventos}
    _eventos_cache[email] = {"ts": now, "data": out}
    return out