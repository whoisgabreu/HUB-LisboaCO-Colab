import os
import re
import time

import psycopg2

try:  # reusa a conexão/schema do dashboard
    from .db import DB_URL, SCHEMA
except Exception:  # noqa: BLE001
    from urllib.parse import quote_plus
    def _fallback_db_url():
        host, port = os.getenv("DB_HOST"), os.getenv("DB_PORT")
        database, user, password = os.getenv("DB_DATABASE"), os.getenv("DB_USERNAME"), os.getenv("DB_PASSWORD")
        if not all([host, port, database, user, password]):
            return None
        return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{database}"
    DB_URL = os.getenv("DB_EXTERNAL_URL") or _fallback_db_url()
    SCHEMA = os.getenv("SCHEMA", "analise_grupos_cliente")

TABLE = "autores"
CACHE_TTL = int(os.getenv("AUTORES_CACHE_TTL", "30"))

_EQUIPE = {}
_CLIENTES = {}
_EQUIPE_NORM = {}
_CLIENTES_NORM = {}
_loaded = False
_ts = 0.0


def _norm(nome):
    if not nome:
        return ""
    return re.sub(r"\s+", " ", str(nome).strip()).lower()


def _exec(query, params=None, fetch=False):
    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            rows = cur.fetchall() if fetch else None
        conn.commit()
        return rows
    finally:
        conn.close()


def _carregar():
    global _EQUIPE, _CLIENTES, _EQUIPE_NORM, _CLIENTES_NORM, _loaded, _ts
    rows = _exec(f'SELECT nome, papel, tipo FROM "{SCHEMA}"."{TABLE}"', fetch=True)
    equipe, clientes = {}, {}
    for nome, papel, tipo in rows:
        if tipo == "cliente":
            clientes[nome] = papel
        else:
            equipe[nome] = papel
    _EQUIPE, _CLIENTES = equipe, clientes
    _EQUIPE_NORM = {_norm(k): v for k, v in equipe.items()}
    _CLIENTES_NORM = {_norm(k): v for k, v in clientes.items()}
    _loaded = True
    _ts = time.time()


def _ensure():
    global _loaded
    if _loaded and (time.time() - _ts) < CACHE_TTL:
        return
    try:
        _carregar()
    except Exception:  # noqa: BLE001 — banco off não deve quebrar a página
        _loaded = True


def _reload():
    try:
        _carregar()
    except Exception:  # noqa: BLE001
        pass


def origem(nome):
    _ensure()
    n = _norm(nome)
    if n in _EQUIPE_NORM:
        return "equipe"
    if n in _CLIENTES_NORM:
        return "cliente"
    return None


def tipo_autor(nome):
    return "equipe" if origem(nome) == "equipe" else "cliente"


def papel(nome):
    _ensure()
    n = _norm(nome)
    if n in _EQUIPE_NORM:
        return _EQUIPE_NORM[n]
    if n in _CLIENTES_NORM:
        return _CLIENTES_NORM[n]
    return None


def classificar(nome):
    return {"tipo": tipo_autor(nome), "papel": papel(nome)}


def papeis_disponiveis():
    _ensure()
    return sorted(set(_EQUIPE.values()) | set(_CLIENTES.values()))


def membros():
    _ensure()
    out = [{"nome": k, "papel": v, "tipo": "equipe"} for k, v in _EQUIPE.items()]
    out += [{"nome": k, "papel": v, "tipo": "cliente"} for k, v in _CLIENTES.items()]
    return sorted(out, key=lambda x: x["nome"].lower())


def adicionar(nome, papel, tipo="equipe"):
    if not nome:
        return False
    nome = nome.strip()
    chave = _norm(nome)
    if not chave:
        return False
    tipo = "cliente" if tipo == "cliente" else "equipe"
    _exec(
        f'INSERT INTO "{SCHEMA}"."{TABLE}" (nome, nome_norm, papel, tipo, atualizado_em) '
        "VALUES (%s, %s, %s, %s, now()) "
        "ON CONFLICT (nome_norm) DO UPDATE SET nome=EXCLUDED.nome, papel=EXCLUDED.papel, "
        "tipo=EXCLUDED.tipo, atualizado_em=now()",
        (nome, chave, papel, tipo),
    )
    _reload()
    return True


def remover(nome):
    chave = _norm(nome)
    if not chave:
        return False
    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DELETE FROM "{SCHEMA}"."{TABLE}" WHERE nome_norm=%s', (chave,))
            removidos = cur.rowcount
        conn.commit()
    finally:
        conn.close()
    if removidos:
        _reload()
        return True
    return False


def nao_mapeados(msgs):
    _ensure()
    cont = {}
    for m in msgs:
        if origem(m["nome"]) is None:
            cont.setdefault(m["nome"], {"lid": m["lid"], "count": 0})
            cont[m["nome"]]["count"] += 1
    return [
        {"nome": k, "lid": v["lid"], "count": v["count"]}
        for k, v in sorted(cont.items(), key=lambda x: -x[1]["count"])
    ]


def dados():
    _ensure()
    return {"equipe": dict(_EQUIPE), "clientes": dict(_CLIENTES)}


def importar(equipe, clientes):
    if not isinstance(equipe, dict) or not isinstance(clientes, dict):
        raise ValueError("Formato inválido para equipe/clientes.")
    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DELETE FROM "{SCHEMA}"."{TABLE}"')
            for tipo, grupo in (("equipe", equipe), ("cliente", clientes)):
                for nome, papel in grupo.items():
                    nn = _norm(nome)
                    if not nn:
                        continue
                    cur.execute(
                        f'INSERT INTO "{SCHEMA}"."{TABLE}" (nome, nome_norm, papel, tipo, atualizado_em) '
                        "VALUES (%s, %s, %s, %s, now()) "
                        "ON CONFLICT (nome_norm) DO UPDATE SET nome=EXCLUDED.nome, papel=EXCLUDED.papel, "
                        "tipo=EXCLUDED.tipo, atualizado_em=now()",
                        (str(nome).strip(), nn, papel, tipo),
                    )
        conn.commit()
    finally:
        conn.close()
    _reload()