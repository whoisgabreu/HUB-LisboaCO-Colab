"""Planejador semanal automático.

Distribui os projetos ativos ao longo de uma semana (seg-sex) em blocos de
tempo, com base nos indicadores já calculados pelo motor (prioridade, esforço,
urgência, risco) e no prazo previsto. Não persiste nada: o resultado é
recalculado a partir da configuração a cada acesso.
"""

from datetime import date, datetime, timedelta

from .domain import label_indicador, label_prioridade, nivel_indicador

DIAS_PADRAO = [
    ("seg", "Segunda"),
    ("ter", "Terça"),
    ("qua", "Quarta"),
    ("qui", "Quinta"),
    ("sex", "Sexta"),
]

AGENDA_PADRAO = {
    "dias": [chave for chave, _ in DIAS_PADRAO],
    "expediente": {"inicio": "09:00", "fim": "18:00"},
    "almoco": {"inicio": "12:00", "fim": "13:00"},
    "slot_min": 30,
    "horas_por_esforco": {
        "pequeno": 2,
        "medio": 4,
        "grande": 8,
        "muito_grande": 14,
    },
}

_ROTULO_DIA = dict(DIAS_PADRAO)

FORMAS = {
    "concentrado": {
        "n": 3,
        "dmax": 180,
        "motivo": "Alta prioridade/esforço — blocos concentrados no início da semana",
    },
    "focado": {
        "n": 3,
        "dmax": 120,
        "motivo": "Prioridade relevante — blocos de foco em dias seguidos",
    },
    "distribuido": {
        "n": 4,
        "dmax": 90,
        "motivo": "Cadência distribuída ao longo da semana",
    },
    "pulverizado": {
        "n": 5,
        "dmax": 60,
        "motivo": "Projeto leve — foco curto uma vez por dia",
    },
    "unico": {
        "n": 1,
        "dmax": 180,
        "motivo": "Baixo esforço — resolvido em um único dia",
    },
}


def _parse_hora(texto, padrao):
    try:
        partes = str(texto).split(":")
        if len(partes) != 2:
            raise ValueError
        hora, minuto = int(partes[0]), int(partes[1])
        if not (0 <= hora <= 23 and 0 <= minuto <= 59):
            raise ValueError
        return hora * 60 + minuto
    except (TypeError, ValueError):
        return padrao


def _fmt_hora(minutos):
    minutos = max(0, int(minutos))
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def _como_data(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor:
        for formato in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(valor[:10], formato).date()
            except ValueError:
                continue
    return None


def _config(cfg):
    agenda = dict(AGENDA_PADRAO)
    agenda.update((cfg or {}).get("agenda") or {})
    expediente = {**AGENDA_PADRAO["expediente"], **(agenda.get("expediente") or {})}
    almoco = {**AGENDA_PADRAO["almoco"], **(agenda.get("almoco") or {})}
    inicio = _parse_hora(expediente.get("inicio"), 540)
    fim = _parse_hora(expediente.get("fim"), 1080)
    if fim <= inicio:
        inicio, fim = 540, 1080
    almoco_inicio = _parse_hora(almoco.get("inicio"), 720)
    almoco_fim = _parse_hora(almoco.get("fim"), 780)
    if not (inicio < almoco_inicio < almoco_fim <= fim):
        almoco_inicio, almoco_fim = None, None
    slot = agenda.get("slot_min")
    slot = int(slot) if isinstance(slot, int) and slot > 0 else 30
    dias = [(chave, _ROTULO_DIA.get(chave, chave)) for chave in agenda.get("dias") or []]
    if not dias:
        dias = list(DIAS_PADRAO)
    return {
        "dias": dias[:5],
        "inicio": inicio,
        "fim": fim,
        "almoco_inicio": almoco_inicio,
        "almoco_fim": almoco_fim,
        "slot": slot,
        "horas_por_esforco": {
            **AGENDA_PADRAO["horas_por_esforco"],
            **(agenda.get("horas_por_esforco") or {}),
        },
    }


def _intervalos_livres(conf):
    inicio = conf["inicio"]
    fim = conf["fim"]
    almoco_ini = conf["almoco_inicio"]
    almoco_fim = conf["almoco_fim"]
    if almoco_ini is None or almoco_ini <= inicio or almoco_fim >= fim:
        return [(inicio, fim)]
    return [(inicio, almoco_ini), (almoco_fim, fim)]


def _round_slot(minutos, slot):
    return max(slot, int(round(minutos / slot)) * slot)


def _segunda_da_semana(quando):
    quando = quando or date.today()
    return quando - timedelta(days=quando.weekday())


def _peso(linha, segunda, sexta):
    analise = linha["analise"]
    projeto = linha["projeto"]
    indice = analise["prioridade"]["indice"]
    esforco = nivel_indicador("esforco", projeto.get("esforco"))
    urgencia = nivel_indicador("urgencia", projeto.get("urgencia"))
    risco = nivel_indicador("risco", projeto.get("risco"))
    peso = (
        0.45 * indice
        + 0.20 * esforco * 25
        + 0.20 * urgencia * 25
        + 0.15 * risco * 25
    )
    previsto = _como_data(projeto.get("data_prevista_fim"))
    if previsto is not None:
        if previsto < segunda:
            peso += 60
        elif previsto <= sexta:
            peso += 30
    return peso


def _forma(prioridade_nivel, esforco_nivel, total_min):
    if esforco_nivel >= 4 or prioridade_nivel == "critica":
        return "concentrado"
    if esforco_nivel == 3 or prioridade_nivel == "alta":
        return "focado"
    if esforco_nivel == 2:
        return "distribuido"
    if total_min <= 90:
        return "unico"
    return "pulverizado"


def _horas_previstas(projeto, esforco_valor, peso_indice, conf):
    base = conf["horas_por_esforco"].get(esforco_valor)
    if base is None:
        base = conf["horas_por_esforco"].get("medio", 4)
    fator = 0.6 + (peso_indice / 100.0) * 0.8
    horas = float(base) * fator
    return max(0.5, horas)


def _plano(total_min, forma, slot):
    spec = FORMAS.get(forma, FORMAS["focado"])
    dmax = spec["dmax"]
    dur = _round_slot(total_min / spec["n"], slot)
    dur = max(slot, min(dur, dmax))
    n = spec["n"]
    while n < 5 and n * dur < total_min:
        n += 1
    return n, dur


def _encaixar(intervalos, dur):
    for indice, (inicio, fim) in enumerate(intervalos):
        if fim - inicio >= dur:
            restante = (inicio + dur, fim)
            if restante[1] > restante[0]:
                intervalos[indice] = restante
            else:
                intervalos.pop(indice)
            return inicio
    return None


def planejar_semana(linhas, cfg, quando=None):
    conf = _config(cfg)
    segunda = _segunda_da_semana(_como_data(quando) if quando else None)
    dias_conf = conf["dias"]
    total_dias = len(dias_conf)
    dias = []
    for posicao, (chave, rotulo) in enumerate(dias_conf):
        dias.append(
            {
                "chave": chave,
                "label": rotulo,
                "data": segunda + timedelta(days=posicao),
            }
        )
    intervalo = _intervalos_livres(conf)

    candidatos = []
    for linha in linhas:
        if linha["projeto"].get("status") != "ativo":
            continue
        candidatos.append(linha)
    candidatos.sort(
        key=lambda linha: _peso(
            linha, segunda, segunda + timedelta(days=total_dias - 1)
        ),
        reverse=True,
    )

    livres = {posicao: list(intervalo) for posicao in range(total_dias)}
    blocos = []
    nao_alocados = []

    for linha in candidatos:
        projeto = linha["projeto"]
        analise = linha["analise"]
        esforco_valor = projeto.get("esforco") or "medio"
        esforco_nivel = nivel_indicador("esforco", esforco_valor)
        prioridade_nivel = analise["prioridade"]["nivel"]
        indice = analise["prioridade"]["indice"]

        horas = _horas_previstas(projeto, esforco_valor, indice, conf)
        total_min = int(round(horas * 60))
        forma = _forma(prioridade_nivel, esforco_nivel, total_min)
        n, dur = _plano(total_min, forma, conf["slot"])

        colocados = 0
        for sessao in range(n):
            inicio = None
            for tentativa in range(total_dias):
                posicao = (sessao + tentativa) % total_dias
                inicio = _encaixar(livres[posicao], dur)
                if inicio is not None:
                    break
            if inicio is None:
                break
            blocos.append(
                {
                    "dia": posicao,
                    "dia_chave": dias[posicao]["chave"],
                    "inicio": _fmt_hora(inicio),
                    "fim": _fmt_hora(inicio + dur),
                    "inicio_min": inicio,
                    "fim_min": inicio + dur,
                    "duracao_min": dur,
                    "projeto": {
                        "id": projeto["id"],
                        "nome": projeto["nome"],
                    },
                    "cor": label_prioridade(prioridade_nivel)["cor"],
                    "prioridade": analise["prioridade"]["label"],
                    "esforco": label_indicador("esforco", esforco_valor),
                    "forma": forma,
                    "motivo": FORMAS[forma]["motivo"],
                }
            )
            colocados += 1

        if colocados == 0:
            nao_alocados.append(
                {
                    "nome": projeto["nome"],
                    "motivo": "Sem espaço na semana",
                }
            )

    bottom = conf["fim"] - conf["inicio"]
    for bloco in blocos:
        bloco["top_pct"] = round(
            (bloco["inicio_min"] - conf["inicio"]) / bottom * 100, 3
        )
        bloco["altura_pct"] = round(bloco["duracao_min"] / bottom * 100, 3)

    por_dia = []
    for posicao, dia in enumerate(dias):
        do_dia = sorted(
            (b for b in blocos if b["dia"] == posicao), key=lambda b: b["inicio_min"]
        )
        por_dia.append(
            {
                "chave": dia["chave"],
                "label": dia["label"],
                "data": dia["data"],
                "blocos": do_dia,
                "minutos": sum(b["duracao_min"] for b in do_dia),
            }
        )

    disponivel = sum(fim - inicio for inicio, fim in intervalo) * total_dias
    planejado = sum(b["duracao_min"] for b in blocos)
    reguas = list(range(conf["inicio"], conf["fim"] + 1, 60))

    return {
        "dias": por_dia,
        "blocos": blocos,
        "regua": reguas,
        "expediente": {
            "inicio": conf["inicio"],
            "fim": conf["fim"],
            "inicio_txt": _fmt_hora(conf["inicio"]),
            "fim_txt": _fmt_hora(conf["fim"]),
        },
        "almoco": {
            "inicio_min": conf["almoco_inicio"],
            "fim_min": conf["almoco_fim"],
            "top_pct": round(
                (conf["almoco_inicio"] - conf["inicio"]) / bottom * 100, 3
            )
            if conf["almoco_inicio"] is not None
            else None,
            "altura_pct": round(
                (conf["almoco_fim"] - conf["almoco_inicio"]) / bottom * 100, 3
            )
            if conf["almoco_inicio"] is not None
            else None,
        },
        "resumo": {
            "projetos": len({b["projeto"]["id"] for b in blocos}),
            "blocos": len(blocos),
            "planejado_min": planejado,
            "disponivel_min": disponivel,
            "ocupacao_pct": round(planejado / disponivel * 100)
            if disponivel
            else 0,
        },
        "nao_alocados": nao_alocados,
        "semana_inicio": segunda,
        "semana_fim": segunda + timedelta(days=total_dias - 1),
        "tem_projetos": bool(candidatos),
    }
