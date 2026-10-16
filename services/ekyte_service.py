import os
import threading
import time
import requests
from concurrent.futures import ThreadPoolExecutor

API_BASE = "https://api.ekyte.com/v1.1"
CACHE_TTL = 60
RAW_CACHE_TTL = 1800  # 30 min — as tarefas mudam pouco; evita raspagem pesada a cada request
JANELA_DIAS = 60  # 2 meses via createdFrom (criadas nesse período)
LOTE = 24
TETO_PAGINAS = 200  # segurança contra loop infinito (20000 tarefas)

_cache = {}
_raw_cache = {}


def _get_api_key() -> str:
    return os.getenv("EKYTE_API_KEY") or ""


def _lower(v: str) -> str:
    return str(v or "").lower().strip()


def _emails_explícitos(item: dict) -> set:
    """E-mails diretos de responsáveis no schema flat da eKyte (executor/coexecutor)."""
    emails = set()
    for chave in ("executorEmail", "coExecutorEmail", "createdByEmail"):
        v = item.get(chave)
        if isinstance(v, str) and "@" in v:
            emails.add(_lower(v))
    return emails


def _colecionar_emails(item) -> set:
    """Fallback: coleta e-mails espalhados em campos de responsável/executor/usuário."""
    emails = set()
    if isinstance(item, dict):
        for k, v in item.items():
            kl = _lower(k)
            if any(s in kl for s in ("responsib", "executor", "owner", "user", "email", "usuario", "assignee")):
                if isinstance(v, str):
                    if "@" in v:
                        emails.add(_lower(v))
                elif isinstance(v, dict):
                    emails.update(_colecionar_emails(v))
                elif isinstance(v, list):
                    for e in v:
                        if isinstance(e, str) and "@" in e:
                            emails.add(_lower(e))
                        elif isinstance(e, dict):
                            emails.update(_colecionar_emails(e))
            else:
                if isinstance(v, dict):
                    emails.update(_colecionar_emails(v))
                elif isinstance(v, list):
                    for e in v:
                        if isinstance(e, dict):
                            emails.update(_colecionar_emails(e))
    elif isinstance(item, list):
        for e in item:
            emails.update(_colecionar_emails(e))
    return emails


def _emails_da_tarefa(item: dict) -> set:
    return _emails_explícitos(item) | _colecionar_emails(item)


def _normalizar_tarefa(item: dict) -> dict:
    def pega(*chaves):
        for c in chaves:
            v = item.get(c)
            if v not in (None, ""):
                if isinstance(v, dict):
                    for sub in v.values():
                        if isinstance(sub, str):
                            return _lower(sub)
                return str(v) if not isinstance(v, (dict, list)) else None
        return None

    url = item.get("url") or item.get("link") or item.get("href")
    prazo = pega("currentDueDate", "dueDate", "endDate", "prazo", "dataEntrega")
    fase = pega("phaseName", "currentPhase", "phase", "etapa", "flowPhase", "etapaAtual")
    workspace = pega("workspaceName", "workspace", "workspaceId", "espaco")

    out = {"id": item.get("id")}
    out["titulo"] = pega("title", "nome", "name") or "Tarefa sem título"
    if fase:
        out["fase"] = fase
    if prazo:
        out["prazo"] = prazo.split("T")[0]
    if workspace:
        out["workspace"] = workspace
    if url:
        out["url"] = url
    return out


def _fetch_pagina(page: int, created_from: str) -> list:
    try:
        from datetime import datetime
        resp = requests.get(
            f"{API_BASE}/tasks",
            params={
                "apiKey": _get_api_key(),
                "createdFrom": created_from,
                "createdTo": datetime.now().strftime("%Y-%m-%d"),
                "status": 0,
                "page": page,
            },
            timeout=20,
        )
        if resp.status_code != 200:
            return []
        payload = resp.json() or {}
        if payload.get("error"):
            return []
        data = payload.get("data")
        if data is None:
            return []
        return data if isinstance(data, list) else (data.get("tasks") or data.get("items") or [])
    except Exception:
        return []


def _raspar_sincrono(created_from: str) -> list:
    """Raspa TODAS as tarefas ativas (100/página) em lotes paralelos, até esvaziar."""
    todas = []
    page = 1
    while page <= TETO_PAGINAS:
        paginas = list(range(page, page + LOTE))
        with ThreadPoolExecutor(max_workers=LOTE) as ex:
            resultados = list(ex.map(lambda p: _fetch_pagina(p, created_from), paginas))

        tijolo_tem_dados = False
        for items in resultados:
            if items:
                tijolo_tem_dados = True
                todas.extend(items)
        if not tijolo_tem_dados:
            break
        page += LOTE
    return todas


_refresh_lock = threading.Lock()
_refreshing = {}

def _refresh_em_andamento(created_from: str) -> bool:
    return bool(_refreshing.get(created_from))


def _refresh_background(created_from: str) -> None:
    try:
        datas = _raspar_sincrono(created_from)
        _raw_cache[created_from] = {"ts": time.time(), "data": datas}
    except Exception:
        pass
    finally:
        with _refresh_lock:
            _refreshing.pop(created_from, None)


def refresh_agora(created_from: str) -> list:
    """Raspagem síncrona forçada (ex.: job agendado) sem disparar thread."""
    try:
        datas = _raspar_sincrono(created_from)
        _raw_cache[created_from] = {"ts": time.time(), "data": datas}
        return datas
    except Exception:
        return _raw_cache.get(created_from, {}).get("data", [])


def _raspar_todas(created_from: str) -> list:
    """Retorna o cache fresco; se estiver velho/vazio, dispara refresh em background sem bloquear."""
    now = time.time()
    cached = _raw_cache.get(created_from)
    if cached and (now - cached["ts"]) < RAW_CACHE_TTL:
        return cached["data"]

    atual = cached["data"] if cached else []
    with _refresh_lock:
        iniciou = not _refreshing.get(created_from)
        if iniciou:
            _refreshing[created_from] = True
    if iniciou:
        threading.Thread(target=_refresh_background, args=(created_from,), daemon=True).start()
    return atual


def _chave_ordenacao(t: dict) -> tuple:
    """Prazo válido primeiro (crescente); sem prazo no fim."""
    prazo = t.get("prazo")
    if isinstance(prazo, str) and len(prazo) >= 10:
        iso = prazo[:10].replace("/", "-")
        try:
            from datetime import datetime
            datetime.strptime(iso, "%Y-%m-%d")
            return (0, iso)
        except ValueError:
            pass
    return (1, "9999-12-31")


def listar_tarefas_do_email(email: str, limite: int = None) -> dict:
    key = _get_api_key()
    if not key:
        return {"erro": "sem_configuracao"}

    ck = f"{_lower(email)}|{limite if limite else 'all'}"
    now = time.time()
    cached = _cache.get(ck)
    if cached and (now - cached["ts"]) < CACHE_TTL:
        return cached["data"]

    try:
        from datetime import datetime, timedelta

        created_from = (datetime.now() - timedelta(days=JANELA_DIAS)).strftime("%Y-%m-%d")
        alvo = _lower(email)

        tarefas = []
        for it in _raspar_todas(created_from):
            if not isinstance(it, dict):
                continue
            if str(it.get("situation")) == "40":  # concluída (defensivo além do status=0)
                continue
            if alvo in _emails_da_tarefa(it):
                tarefas.append(_normalizar_tarefa(it))

        tarefas.sort(key=_chave_ordenacao)
        total = len(tarefas)
        if limite and limite > 0:
            tarefas = tarefas[:limite]

        out = {"tarefas": tarefas, "total": total}
        if _refresh_em_andamento(created_from):
            out["atualizando"] = True
        _cache[ck] = {"ts": time.time(), "data": out}
        return out
    except Exception:
        return {"erro": "api"}