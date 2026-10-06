import os
import time

from dotenv import load_dotenv
import psycopg2
from datetime import datetime

from .nomes import limpar_nome_grupo

load_dotenv()


def _fallback_db_url():
    """Reaproveita as variáveis DB_* do HUB quando DB_EXTERNAL_URL não existe."""
    from urllib.parse import quote_plus

    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    database = os.getenv("DB_DATABASE")
    user = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")
    if not all([host, port, database, user, password]):
        return None
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{database}"


DB_URL = os.getenv("DB_EXTERNAL_URL") or _fallback_db_url()
SCHEMA = os.getenv("SCHEMA", "analise_grupos_cliente")
TABLE = os.getenv("TABLE", "mensagens_coletadas")
TABLE_GRUPOS = os.getenv("TABLE_GRUPOS", "group_id")
CACHE_TTL = int(os.getenv("DG_CACHE_TTL", "30"))

_cache = {"ts": 0, "data": None}
_cache_grupos = {"ts": 0, "data": None}


def _parse_ts(data, hora):
    if not data:
        return None
    s = f"{data} {hora or '00:00:00'}".strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def get_grupos(force=False):
    global _cache_grupos
    if not force and _cache_grupos["data"] is not None and time.time() - _cache_grupos["ts"] < CACHE_TTL:
        return _cache_grupos["data"]
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f'SELECT id, group_name, group_lid FROM "{SCHEMA}"."{TABLE_GRUPOS}" ORDER BY group_name')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    grupos = [{"id": r[0], "name": limpar_nome_grupo(r[1]), "lid": r[2]} for r in rows]
    _cache_grupos = {"ts": time.time(), "data": grupos}
    return grupos


def get_mensagens(force=False):
    global _cache
    if not force and _cache["data"] is not None and time.time() - _cache["ts"] < CACHE_TTL:
        return _cache["data"]
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(
        f'SELECT id, "pushName", message, lid, data, hora, "nome_do_grupo" '
        f'FROM "{SCHEMA}"."{TABLE}"'
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    lid_por_grupo = {g["name"]: g["lid"] for g in get_grupos()}
    msgs = []
    for rid, nome, texto, lid, data, hora, grupo in rows:
        grupo_limpo = limpar_nome_grupo(grupo)
        msgs.append({
            "id": rid,
            "nome": nome,
            "texto": texto,
            "lid": lid,
            "grupo": grupo_limpo,
            "group_lid": lid_por_grupo.get(grupo_limpo),
            "ts": _parse_ts(data, hora),
            "data": data,
            "hora": hora,
        })
    msgs = [m for m in msgs if m["ts"] is not None]
    msgs.sort(key=lambda m: (m["ts"], m["id"]))
    _cache = {"ts": time.time(), "data": msgs}
    return msgs