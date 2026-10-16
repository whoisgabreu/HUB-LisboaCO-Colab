from datetime import date, datetime

from ..domain import RITMO, nivel_indicador


def _como_data(valor):
    if isinstance(valor, datetime):
        return valor.date()
    return valor


def _dias_desde(valor, hoje):
    valor = _como_data(valor)
    if not valor:
        return None
    return (hoje - valor).days


def calcular_progresso(etapas):
    total = len(etapas)
    if not total:
        return 0.0
    concluidas = sum(1 for e in etapas if e.get("status") == "concluida")
    return concluidas / total


def _progresso_esperado(projeto, etapas, hoje):
    total = len(etapas)
    previstas = [e for e in etapas if e.get("data_prevista")]
    if total and previstas:
        vencidas = sum(1 for e in previstas if _como_data(e["data_prevista"]) <= hoje)
        return min(vencidas / total, 1.0)
    inicio = _como_data(projeto.get("data_inicio"))
    fim = _como_data(projeto.get("data_prevista_fim"))
    if inicio and fim and fim > inicio:
        decorrido = (hoje - inicio).days
        duracao = (fim - inicio).days
        return max(0.0, min(decorrido / duracao, 1.0))
    return None


def _ritmo_por_delta(delta, limiares):
    if delta is None:
        return "fluindo"
    for limiar in limiares:
        if delta >= limiar["min"]:
            return limiar["ritmo"]
    return "muito_lento"


def _rebaixar(ritmo, alvo):
    if RITMO[ritmo]["nivel"] > RITMO[alvo]["nivel"]:
        return alvo
    return ritmo


def calcular_saude(projeto, etapas, cfg, hoje=None):
    hoje = hoje or date.today()
    total = len(etapas)
    concluidas = sum(1 for e in etapas if e.get("status") == "concluida")
    progresso = concluidas / total if total else 0.0
    esperado = _progresso_esperado(projeto, etapas, hoje)
    delta = progresso - esperado if esperado is not None else None
    etapas_vencidas = sum(
        1
        for etapa in etapas
        if etapa.get("status") != "concluida"
        and etapa.get("data_prevista")
        and _como_data(etapa["data_prevista"]) < hoje
    )

    concluidas_ids = {etapa["id"] for etapa in etapas if etapa.get("status") == "concluida"}
    dependencias_bloqueadas = sum(
        1
        for etapa in etapas
        if etapa.get("dependencia_id")
        and etapa.get("status") != "concluida"
        and etapa["dependencia_id"] not in concluidas_ids
    )

    dias_bloqueio = None
    for etapa in etapas:
        if etapa.get("bloqueada") and etapa.get("bloqueio_desde"):
            dias = _dias_desde(etapa["bloqueio_desde"], hoje)
            if dias is not None:
                dias_bloqueio = max(dias_bloqueio or 0, dias)

    marcas = [projeto.get("updated_at")] + [e.get("updated_at") for e in etapas]
    marcas = [m for m in marcas if m]
    ultima = max(marcas) if marcas else None
    dias_sem_movimento = _dias_desde(ultima, hoje)

    saude_cfg = cfg["saude"]
    if projeto.get("ritmo_manual"):
        ritmo = projeto["ritmo_manual"]
        origem = "manual"
    else:
        ritmo = _ritmo_por_delta(delta, saude_cfg["limiares_ritmo"])
        origem = "automatico"

    if (
        dias_bloqueio is not None
        and dias_bloqueio >= saude_cfg["dias_bloqueio_alerta"]
    ):
        ritmo = _rebaixar(ritmo, "lento")

    if (
        projeto.get("status") == "ativo"
        and dias_sem_movimento is not None
        and dias_sem_movimento >= saude_cfg["dias_sem_movimento"]
    ):
        ritmo = _rebaixar(ritmo, "lento")

    if dependencias_bloqueadas:
        ritmo = _rebaixar(ritmo, "lento")

    return {
        "progresso": progresso,
        "progresso_pct": round(progresso * 100),
        "concluidas": concluidas,
        "total": total,
        "esperado": round(esperado, 2) if esperado is not None else None,
        "delta": round(delta, 2) if delta is not None else None,
        "ritmo": ritmo,
        "ritmo_origem": origem,
        "ritmo_nivel": nivel_indicador("ritmo", ritmo),
        "dias_bloqueio": dias_bloqueio,
        "dias_sem_movimento": dias_sem_movimento,
        "etapas_vencidas": etapas_vencidas,
        "dependencias_bloqueadas": dependencias_bloqueadas,
    }
