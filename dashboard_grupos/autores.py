import json
import os
import re

BASE = os.path.dirname(__file__)

EQUIPE_PATH = os.environ.get("EQUIPE_PATH", os.path.join(BASE, "..", "equipe.json"))
CLIENTES_PATH = os.environ.get("CLIENTES_PATH", os.path.join(BASE, "..", "clientes.json"))


def _norm(nome):
    if not nome:
        return ""
    return re.sub(r"\s+", " ", nome.strip()).lower()


def _load(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


_EQUIPE = _load(EQUIPE_PATH)
_CLIENTES = _load(CLIENTES_PATH)
_EQUIPE_NORM = {_norm(k): v for k, v in _EQUIPE.items()}
_CLIENTES_NORM = {_norm(k): v for k, v in _CLIENTES.items()}


def _reload():
    global _EQUIPE, _CLIENTES, _EQUIPE_NORM, _CLIENTES_NORM
    _EQUIPE = _load(EQUIPE_PATH)
    _CLIENTES = _load(CLIENTES_PATH)
    _EQUIPE_NORM = {_norm(k): v for k, v in _EQUIPE.items()}
    _CLIENTES_NORM = {_norm(k): v for k, v in _CLIENTES.items()}


def origem(nome):
    n = _norm(nome)
    if n in _EQUIPE_NORM:
        return "equipe"
    if n in _CLIENTES_NORM:
        return "cliente"
    return None


def tipo_autor(nome):
    return "equipe" if origem(nome) == "equipe" else "cliente"


def papel(nome):
    n = _norm(nome)
    if n in _EQUIPE_NORM:
        return _EQUIPE_NORM[n]
    if n in _CLIENTES_NORM:
        return _CLIENTES_NORM[n]
    return None


def classificar(nome):
    return {"tipo": tipo_autor(nome), "papel": papel(nome)}


def papeis_disponiveis():
    return sorted(set(_EQUIPE.values()) | set(_CLIENTES.values()))


def membros():
    out = [{"nome": k, "papel": v, "tipo": "equipe"} for k, v in _EQUIPE.items()]
    out += [{"nome": k, "papel": v, "tipo": "cliente"} for k, v in _CLIENTES.items()]
    return sorted(out, key=lambda x: x["nome"].lower())


def adicionar(nome, papel, tipo="equipe"):
    chave = _norm(nome)
    if not chave:
        return False
    nome = nome.strip()
    if tipo == "cliente":
        _CLIENTES[nome] = papel
        _save(CLIENTES_PATH, _CLIENTES)
    else:
        _EQUIPE[nome] = papel
        _save(EQUIPE_PATH, _EQUIPE)
    _reload()
    return True


def remover(nome):
    chave = _norm(nome)
    for data, path in ((_EQUIPE, EQUIPE_PATH), (_CLIENTES, CLIENTES_PATH)):
        original = next((k for k in data if _norm(k) == chave), None)
        if original is not None:
            data.pop(original, None)
            _save(path, data)
            _reload()
            return True
    return False


def nao_mapeados(msgs):
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
    """Retorna o mapeamento completo (equipe + clientes) para exportação."""
    return {"equipe": dict(_EQUIPE), "clientes": dict(_CLIENTES)}


def importar(equipe, clientes):
    """Substitui o mapeamento a partir de um dicionário e recarrega."""
    if not isinstance(equipe, dict) or not isinstance(clientes, dict):
        raise ValueError("Formato inválido para equipe/clientes.")
    _save(EQUIPE_PATH, equipe)
    _save(CLIENTES_PATH, clientes)
    _reload()