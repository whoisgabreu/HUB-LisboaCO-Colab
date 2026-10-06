import json
import os
from datetime import time

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")


def _load():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


_CONFIG = _load()


def _parse_time(s):
    h, m = s.split(":")
    return time(int(h), int(m))


def atendimento():
    cfg = _CONFIG.get("atendimento", {})
    return {
        "inicio": _parse_time(cfg.get("inicio", "08:00")),
        "fim": _parse_time(cfg.get("fim", "18:00")),
        "dias_uteis": cfg.get("dias_uteis", True),
    }


def metas():
    cfg = _CONFIG.get("metas", {})
    return {
        "equipe_para_cliente_min": cfg.get("equipe_para_cliente_min", 60),
        "cliente_para_equipe_min": cfg.get("cliente_para_equipe_min", 180),
    }


def get(key, default=None):
    return _CONFIG.get(key, default)


def inatividade():
    return _CONFIG.get("inatividade_dias", 3)


def atual():
    """Retorna uma cópia da configuração completa (para edição)."""
    default = {
        "atendimento": {"inicio": "08:00", "fim": "18:00", "dias_uteis": True},
        "metas": {"equipe_para_cliente_min": 60, "cliente_para_equipe_min": 180},
        "inatividade_dias": 3,
    }
    cfg = dict(_CONFIG)
    for chave, valor in default.items():
        if chave not in cfg:
            cfg[chave] = valor
        elif isinstance(valor, dict):
            cfg[chave] = {**valor, **cfg[chave]}
    return cfg


def salvar(dados):
    """Persiste a configuração e recarrega em memória (sem reiniciar)."""
    global _CONFIG
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    _CONFIG = _load()