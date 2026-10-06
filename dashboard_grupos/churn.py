import json
import os

from .nomes import limpar_nome_grupo

BASE = os.path.dirname(__file__)
CHURN_PATH = os.environ.get("CHURN_PATH", os.path.join(BASE, "..", "churn.json"))


def _load():
    if not os.path.exists(CHURN_PATH):
        return {}
    with open(CHURN_PATH, encoding="utf-8") as f:
        return json.load(f)


_CHURN = _load()
_CHURN_NORM = {limpar_nome_grupo(k): v for k, v in _CHURN.items()}


def _save():
    with open(CHURN_PATH, "w", encoding="utf-8") as f:
        json.dump(_CHURN, f, ensure_ascii=False, indent=2)


def _reload():
    global _CHURN, _CHURN_NORM
    _CHURN = _load()
    _CHURN_NORM = {limpar_nome_grupo(k): v for k, v in _CHURN.items()}


def e_churn(nome):
    return limpar_nome_grupo(nome) in _CHURN_NORM


def lista():
    return [{"nome": k, "lid": v} for k, v in sorted(_CHURN_NORM.items(), key=lambda x: x[0].lower())]


def marcar(nome, lid):
    if not nome:
        return False
    _CHURN[limpar_nome_grupo(nome)] = lid or ""
    _save()
    _reload()
    return True


def desmarcar(nome):
    alvo = limpar_nome_grupo(nome)
    chaves = [k for k in _CHURN if limpar_nome_grupo(k) == alvo]
    if not chaves:
        return False
    for k in chaves:
        _CHURN.pop(k, None)
    _save()
    _reload()
    return True


def filtrar_msgs(msgs):
    return [m for m in msgs if not e_churn(m["grupo"])]


def filtrar_registro(grupos_registro):
    return [g for g in grupos_registro if not e_churn(g["name"])]


def dados():
    """Retorna o mapa de churn para exportação."""
    return dict(_CHURN)


def importar(mapa):
    """Substitui o mapa de churn a partir de um dicionário e recarrega."""
    global _CHURN
    if not isinstance(mapa, dict):
        raise ValueError("Formato inválido para churn.")
    _CHURN = dict(mapa)
    _save()
    _reload()
