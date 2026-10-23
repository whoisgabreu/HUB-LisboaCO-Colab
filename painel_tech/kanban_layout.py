"""Configuração visual do Kanban sem alterar o domínio de projetos.

As colunas desta camada são *lanes* de apresentação. Cada uma aponta para um
dos status exibidos no quadro, inclusive ``finalizado``.
"""

import re
import threading
from copy import deepcopy
from uuid import uuid4

from .config import get_config, save_config
from .domain import STATUS


CONFIG_KEY = "kanban"
MAX_COLUNAS = 24
MAX_NOME = 48
STATUS_QUADRO = ("fila", "ativo", "pausado", "finalizado")

_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
_COR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_LOCK = threading.RLock()

_CORES_PADRAO = {
    "fila": "#D99000",
    "ativo": "#2563EB",
    "pausado": "#64748B",
    "finalizado": "#159766",
}


class ErroLayoutKanban(ValueError):
    """Payload de configuração visual inválido."""


def _colunas_padrao():
    return [
        {
            "id": status,
            "nome": STATUS[status]["label"],
            "cor": _CORES_PADRAO[status],
            "status_base": status,
            "ordem": ordem,
        }
        for ordem, status in enumerate(STATUS_QUADRO)
    ]


def _novo_id():
    return f"coluna-{uuid4().hex[:12]}"


def _id_padrao_disponivel(status, ids):
    candidato = status
    sufixo = 2
    while candidato in ids:
        candidato = f"{status}-padrao-{sufixo}"
        sufixo += 1
    return candidato


def _nome(valor):
    return " ".join(str(valor or "").strip().split())


def _normalizar_coluna(bruta, ordem, *, gerar_id=False):
    if not isinstance(bruta, dict):
        raise ErroLayoutKanban("Cada coluna deve ser um objeto.")

    coluna_id = str(bruta.get("id") or "").strip()
    if not coluna_id and gerar_id:
        coluna_id = _novo_id()
    if not _ID_RE.fullmatch(coluna_id):
        raise ErroLayoutKanban("Identificador de coluna inválido.")

    nome = _nome(bruta.get("nome"))
    if not nome:
        raise ErroLayoutKanban("Todas as colunas precisam de um nome.")
    if len(nome) > MAX_NOME:
        raise ErroLayoutKanban(
            f"O nome de uma coluna pode ter no máximo {MAX_NOME} caracteres."
        )

    cor = str(bruta.get("cor") or "").strip().upper()
    if not _COR_RE.fullmatch(cor):
        raise ErroLayoutKanban("Escolha uma cor válida para cada coluna.")

    status_base = str(bruta.get("status_base") or "").strip()
    if status_base not in STATUS_QUADRO:
        raise ErroLayoutKanban("O comportamento da coluna é inválido.")

    return {
        "id": coluna_id,
        "nome": nome,
        "cor": cor,
        "status_base": status_base,
        "ordem": ordem,
    }


def _normalizar_colunas_salvas(colunas):
    """Recupera o que for válido e garante uma lane para cada status-base."""
    resultado = []
    ids = set()
    if isinstance(colunas, list):
        for bruta in colunas[:MAX_COLUNAS]:
            try:
                coluna = _normalizar_coluna(bruta, len(resultado))
            except ErroLayoutKanban:
                continue
            if coluna["id"] in ids:
                continue
            ids.add(coluna["id"])
            resultado.append(coluna)

    if not resultado:
        return _colunas_padrao()

    status_presentes = {coluna["status_base"] for coluna in resultado}
    for padrao in _colunas_padrao():
        if padrao["status_base"] not in status_presentes:
            padrao["ordem"] = len(resultado)
            if padrao["id"] in ids:
                padrao["id"] = _id_padrao_disponivel(
                    padrao["status_base"], ids
                )
            ids.add(padrao["id"])
            resultado.append(padrao)
    return resultado


def _normalizar_atribuicoes(atribuicoes, ids_validos):
    if not isinstance(atribuicoes, dict):
        return {}
    return {
        str(projeto_id): coluna_id
        for projeto_id, coluna_id in atribuicoes.items()
        if str(projeto_id).isdigit() and coluna_id in ids_validos
    }


def carregar(config=None):
    config = config if config is not None else get_config()
    bruto = config.get(CONFIG_KEY, {})
    if not isinstance(bruto, dict):
        bruto = {}
    colunas = _normalizar_colunas_salvas(bruto.get("colunas"))
    ids = {coluna["id"] for coluna in colunas}
    return {
        "versao": 1,
        "colunas": colunas,
        "atribuicoes": _normalizar_atribuicoes(bruto.get("atribuicoes"), ids),
    }


def _validar_novas_colunas(colunas):
    if not isinstance(colunas, list):
        raise ErroLayoutKanban("Envie uma lista de colunas.")
    if len(colunas) < len(STATUS_QUADRO):
        raise ErroLayoutKanban(
            "Mantenha ao menos uma coluna para cada comportamento do projeto."
        )
    if len(colunas) > MAX_COLUNAS:
        raise ErroLayoutKanban(f"O Kanban aceita no máximo {MAX_COLUNAS} colunas.")

    resultado = []
    ids = set()
    for ordem, bruta in enumerate(colunas):
        coluna = _normalizar_coluna(bruta, ordem, gerar_id=True)
        if coluna["id"] in ids:
            raise ErroLayoutKanban("Existem colunas com o mesmo identificador.")
        ids.add(coluna["id"])
        resultado.append(coluna)

    ausentes = [
        STATUS[status]["label"]
        for status in STATUS_QUADRO
        if not any(coluna["status_base"] == status for coluna in resultado)
    ]
    if ausentes:
        raise ErroLayoutKanban(
            "Mantenha ao menos uma coluna para: " + ", ".join(ausentes) + "."
        )
    return resultado


def salvar_colunas(colunas):
    novas = _validar_novas_colunas(colunas)
    ids_validos = {coluna["id"] for coluna in novas}
    with _LOCK:
        config = get_config()
        atual = carregar(config)
        status_anteriores = {
            coluna["id"]: coluna["status_base"] for coluna in atual["colunas"]
        }
        status_novos = {
            coluna["id"]: coluna["status_base"] for coluna in novas
        }
        atribuicoes = {
            projeto_id: coluna_id
            for projeto_id, coluna_id in atual["atribuicoes"].items()
            if coluna_id in ids_validos
            and status_anteriores.get(coluna_id) == status_novos.get(coluna_id)
        }
        estado = {
            "versao": 1,
            "colunas": novas,
            "atribuicoes": atribuicoes,
        }
        config[CONFIG_KEY] = estado
        save_config(config)
    return deepcopy(estado)


def obter_coluna(coluna_id, config=None):
    for coluna in carregar(config)["colunas"]:
        if coluna["id"] == coluna_id:
            return deepcopy(coluna)
    raise ErroLayoutKanban("A coluna escolhida não existe mais.")


def atribuir_projeto(projeto_id, coluna_id, status_base):
    with _LOCK:
        config = get_config()
        estado = carregar(config)
        coluna = next(
            (item for item in estado["colunas"] if item["id"] == coluna_id), None
        )
        if coluna is None:
            raise ErroLayoutKanban("A coluna escolhida não existe mais.")
        if coluna["status_base"] != status_base:
            raise ErroLayoutKanban("A coluna não corresponde ao status informado.")
        estado["atribuicoes"][str(int(projeto_id))] = coluna_id
        config[CONFIG_KEY] = estado
        save_config(config)
    return deepcopy(coluna)


def aplicar_contexto(contexto):
    """Acrescenta as lanes visuais sem alterar o contexto/listagem original."""
    estado = carregar()
    colunas = [dict(coluna, linhas=[]) for coluna in estado["colunas"]]
    por_id = {coluna["id"]: coluna for coluna in colunas}
    padrao_por_status = {}
    for coluna in colunas:
        padrao_por_status.setdefault(coluna["status_base"], coluna)

    grupos_status = contexto.get("colunas", {})
    for status_base in STATUS_QUADRO:
        for linha in grupos_status.get(status_base, []):
            projeto = linha["projeto"]
            atribuida = por_id.get(
                estado["atribuicoes"].get(str(projeto.get("id")))
            )
            destino = (
                atribuida
                if atribuida and atribuida["status_base"] == projeto.get("status")
                else padrao_por_status.get(projeto.get("status"))
            )
            if destino is not None:
                destino["linhas"].append(linha)

    novo_contexto = dict(contexto)
    novo_contexto["kanban_colunas"] = colunas
    novo_contexto["kanban_status"] = [
        {"chave": status, "label": STATUS[status]["label"]}
        for status in STATUS_QUADRO
    ]
    return novo_contexto
