import statistics
from datetime import datetime, timedelta

from .config import atendimento, metas
from .autores import classificar


def enriquecer(msgs):
    for m in msgs:
        m.update(classificar(m["nome"]))
    return msgs


def resumo_geral(msgs):
    ts = [m["ts"] for m in msgs]
    if not ts:
        return None
    return {
        "total": len(msgs),
        "remetentes": len({m["lid"] for m in msgs}),
        "grupos": len({m["grupo"] for m in msgs}),
        "inicio": min(ts),
        "fim": max(ts),
        "msgs_equipe": sum(1 for m in msgs if m["tipo"] == "equipe"),
        "msgs_cliente": sum(1 for m in msgs if m["tipo"] == "cliente"),
        "dias": len({m["data"] for m in msgs}),
    }


def qualidade(msgs):
    return {
        "sem_texto": sum(1 for m in msgs if m["texto"] is None),
        "sem_grupo": sum(1 for m in msgs if not m["grupo"]),
        "sem_data": sum(1 for m in msgs if not m["data"]),
    }


def tempo_util(de_ts, ate_ts):
    if not de_ts or not ate_ts or de_ts >= ate_ts:
        return 0.0
    a = atendimento()
    total = 0.0
    dia = de_ts.date()
    ultimo = ate_ts.date()
    while dia <= ultimo:
        if not (a["dias_uteis"] and dia.weekday() >= 5):
            wi = datetime.combine(dia, a["inicio"])
            wf = datetime.combine(dia, a["fim"])
            ini = max(de_ts, wi)
            fim = min(ate_ts, wf)
            if fim > ini:
                total += (fim - ini).total_seconds() / 60
        dia += timedelta(days=1)
    return total


def _gran_label(ts, gran):
    if gran == "dia":
        return ts.strftime("%Y-%m-%d")
    if gran == "semana":
        iso = ts.isocalendar()
        return f"{iso[0]}-S{iso[1]:02d}"
    return ts.strftime("%Y-%m")


def serie(msgs, gran="dia"):
    cont = {}
    for m in msgs:
        lbl = _gran_label(m["ts"], gran)
        cont[lbl] = cont.get(lbl, 0) + 1
    return [[k, cont[k]] for k in sorted(cont)]


def distribuicao_hora(msgs):
    cont = [0] * 24
    for m in msgs:
        cont[m["ts"].hour] += 1
    return cont


def heatmap(msgs):
    grid = [[0] * 24 for _ in range(7)]
    for m in msgs:
        grid[m["ts"].weekday()][m["ts"].hour] += 1
    return grid


def comparar_periodos(msgs):
    vazio = {
        "series": [],
        "totais": [0, 0],
        "delta_pct": 0,
        "metade1_ini": None, "metade1_fim": None,
        "metade2_ini": None, "metade2_fim": None,
    }
    if not msgs:
        return vazio
    ts = sorted(m["ts"] for m in msgs)
    inicio, fim = ts[0], ts[-1]
    total_dias = (fim.date() - inicio.date()).days
    prim_dias = max(1, (total_dias + 1) // 2)
    meio_data = inicio.date() + timedelta(days=prim_dias)
    antes = [m for m in msgs if m["ts"].date() < meio_data]
    depois = [m for m in msgs if m["ts"].date() >= meio_data]
    cont_a = dict(serie(antes, "dia"))
    cont_d = dict(serie(depois, "dia"))
    labels = sorted(set(cont_a) | set(cont_d))
    series = [[l, cont_a.get(l, 0), cont_d.get(l, 0)] for l in labels]
    tot1 = sum(v[1] for v in series)
    tot2 = sum(v[2] for v in series)
    delta = round((tot2 - tot1) / tot1 * 100, 1) if tot1 else (100.0 if tot2 else 0.0)
    return {
        "series": series,
        "totais": [tot1, tot2],
        "delta_pct": delta,
        "metade1_ini": min(m["ts"].date() for m in antes) if antes else None,
        "metade1_fim": max(m["ts"].date() for m in antes) if antes else None,
        "metade2_ini": min(m["ts"].date() for m in depois) if depois else None,
        "metade2_fim": max(m["ts"].date() for m in depois) if depois else None,
    }


def top_grupos(msgs, n=10):
    cont = {}
    for m in msgs:
        cont[m["grupo"]] = cont.get(m["grupo"], 0) + 1
    return [[k, v] for k, v in sorted(cont.items(), key=lambda x: -x[1])[:n]]


def top_remetentes(msgs, n=10):
    cont = {}
    for m in msgs:
        cont[m["nome"]] = cont.get(m["nome"], 0) + 1
    return [[k, v] for k, v in sorted(cont.items(), key=lambda x: -x[1])[:n]]


def por_papel(msgs):
    cont = {}
    for m in msgs:
        if m["papel"]:
            cont[m["papel"]] = cont.get(m["papel"], 0) + 1
    return [[k, v] for k, v in sorted(cont.items(), key=lambda x: -x[1])]


def _turns(grupo_msgs):
    ordered = sorted(grupo_msgs, key=lambda m: (m["ts"], m["id"]))
    turns = []
    for m in ordered:
        if m["texto"] is None:
            continue
        if turns and turns[-1]["tipo"] == m["tipo"]:
            turns[-1]["end"] = m["ts"]
            turns[-1]["n"] += 1
        else:
            turns.append({"tipo": m["tipo"], "start": m["ts"], "end": m["ts"], "n": 1})
    return turns


def _tempos_direcao(turns, de, para):
    bruto, util, sem = [], [], 0
    pendente = None
    for t in turns:
        if t["tipo"] == de:
            pendente = t
        elif t["tipo"] == para and pendente is not None:
            bruto.append((t["start"] - pendente["end"]).total_seconds() / 60)
            util.append(tempo_util(pendente["end"], t["start"]))
            pendente = None
    if pendente is not None:
        sem += 1
    return bruto, util, sem


def _percentil(dados, p):
    if not dados:
        return None
    ordenado = sorted(dados)
    k = (len(ordenado) - 1) * p / 100
    f = int(k)
    c = f + 1 if f + 1 < len(ordenado) else f
    return ordenado[f] + (ordenado[c] - ordenado[f]) * (k - f)


def sla_resumo(tempos):
    if not tempos:
        return {"n": 0, "media": None, "p50": None, "p90": None, "min": None, "max": None}
    return {
        "n": len(tempos),
        "media": round(statistics.mean(tempos), 1),
        "p50": round(_percentil(tempos, 50), 1),
        "p90": round(_percentil(tempos, 90), 1),
        "min": round(min(tempos), 1),
        "max": round(max(tempos), 1),
    }


def _taxa(respostas, sem_resposta):
    total = len(respostas) + sem_resposta
    if not total:
        return 0
    return round(len(respostas) / total * 100, 1)


def _resumo_direcao(bruto, util, sem_msgs, resp_msgs, meta_ok_msgs, meta_min):
    total = resp_msgs + sem_msgs
    return {
        "bruto": sla_resumo(bruto),
        "util": sla_resumo(util),
        "sem_resposta": sem_msgs,
        "taxa_resposta": round(resp_msgs / total * 100, 1) if total else 0,
        "pct_dentro_meta": round(meta_ok_msgs / total * 100, 1) if total else 0,
        "meta_min": meta_min,
    }


def _coleta_direcao(grupo_msgs, de, para, meta_min):
    turns = _turns(grupo_msgs)
    bruto, util = [], []
    sem_msgs = resp_msgs = meta_ok_msgs = 0
    pendente = None
    for t in turns:
        if t["tipo"] == de:
            pendente = t
        elif t["tipo"] == para and pendente is not None:
            b = (t["start"] - pendente["end"]).total_seconds() / 60
            u = tempo_util(pendente["end"], t["start"])
            bruto.append(b)
            util.append(u)
            resp_msgs += pendente["n"]
            if u <= meta_min:
                meta_ok_msgs += pendente["n"]
            pendente = None
    if pendente is not None:
        sem_msgs += pendente["n"]
    return bruto, util, sem_msgs, resp_msgs, meta_ok_msgs


def _direcao_info(grupo_msgs, de, para, meta_min):
    return _resumo_direcao(*_coleta_direcao(grupo_msgs, de, para, meta_min), meta_min)


def gaps(turns):
    out = []
    for i in range(1, len(turns)):
        out.append((turns[i]["start"] - turns[i - 1]["end"]).total_seconds() / 60)
    return out


def gaps_resumo(gaps_min):
    if not gaps_min:
        return {"n": 0, "media": None, "max": None, "p50": None}
    return {
        "n": len(gaps_min),
        "media": round(statistics.mean(gaps_min), 1),
        "max": round(max(gaps_min), 1),
        "p50": round(_percentil(gaps_min, 50), 1),
    }


def por_grupo(msgs):
    grupos = {}
    for m in msgs:
        grupos.setdefault(m["grupo"], []).append(m)
    return grupos


def sla_por_grupo(msgs):
    m = metas()
    resultado = {}
    for nome, lista in por_grupo(msgs).items():
        turns = _turns(lista)
        resultado[nome] = {
            "equipe_para_cliente": _direcao_info(lista, "cliente", "equipe", m["equipe_para_cliente_min"]),
            "cliente_para_equipe": _direcao_info(lista, "equipe", "cliente", m["cliente_para_equipe_min"]),
            "gaps": gaps_resumo(gaps(turns)),
            "total": len(lista),
        }
    return resultado


def sla_geral(msgs):
    m = metas()
    acc = {
        "e": {"bruto": [], "util": [], "sem": 0, "resp": 0, "meta_ok": 0},
        "c": {"bruto": [], "util": [], "sem": 0, "resp": 0, "meta_ok": 0},
    }
    for lista in por_grupo(msgs).values():
        for k, de, para, meta in (
            ("e", "cliente", "equipe", m["equipe_para_cliente_min"]),
            ("c", "equipe", "cliente", m["cliente_para_equipe_min"]),
        ):
            b, u, s, r, mk = _coleta_direcao(lista, de, para, meta)
            a = acc[k]
            a["bruto"] += b
            a["util"] += u
            a["sem"] += s
            a["resp"] += r
            a["meta_ok"] += mk
    return {
        "equipe_para_cliente": _resumo_direcao(
            acc["e"]["bruto"], acc["e"]["util"], acc["e"]["sem"],
            acc["e"]["resp"], acc["e"]["meta_ok"], m["equipe_para_cliente_min"]),
        "cliente_para_equipe": _resumo_direcao(
            acc["c"]["bruto"], acc["c"]["util"], acc["c"]["sem"],
            acc["c"]["resp"], acc["c"]["meta_ok"], m["cliente_para_equipe_min"]),
    }


def msgs_sem_resposta(msgs, de, para):
    out = []
    for glista in por_grupo(msgs).values():
        ordered = sorted(glista, key=lambda x: (x["ts"], x["id"]))
        n = len(ordered)
        tem_apos = [False] * n
        visto = False
        for i in range(n - 1, -1, -1):
            tem_apos[i] = visto
            if ordered[i]["tipo"] == para and ordered[i]["texto"] is not None:
                visto = True
        for i, m in enumerate(ordered):
            if m["tipo"] != de or m["texto"] is None:
                continue
            if not tem_apos[i]:
                out.append({
                    "id": m["id"],
                    "grupo": m["grupo"],
                    "nome": m["nome"],
                    "tipo": m["tipo"],
                    "papel": m["papel"],
                    "ts": m["ts"],
                    "texto": m["texto"],
                })
    out.sort(key=lambda x: x["ts"])
    return out


def sla_por_hora(msgs, de, para):
    horas = {}
    for lista in por_grupo(msgs).values():
        turns = _turns(lista)
        pendente = None
        for t in turns:
            if t["tipo"] == de:
                pendente = t
            elif t["tipo"] == para and pendente is not None:
                h = pendente["end"].hour
                horas.setdefault(h, []).append(tempo_util(pendente["end"], t["start"]))
                pendente = None
    return [
        [h, round(statistics.mean(horas[h]), 1) if h in horas else None, len(horas.get(h, []))]
        for h in range(24)
    ]


_DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def sla_por_dia_semana(msgs, de, para):
    dias = {}
    for lista in por_grupo(msgs).values():
        turns = _turns(lista)
        pendente = None
        for t in turns:
            if t["tipo"] == de:
                pendente = t
            elif t["tipo"] == para and pendente is not None:
                d = pendente["end"].weekday()
                dias.setdefault(d, []).append(tempo_util(pendente["end"], t["start"]))
                pendente = None
    return [
        [_DIAS_SEMANA[d], round(statistics.mean(dias[d]), 1) if d in dias else None, len(dias.get(d, []))]
        for d in range(7)
    ]


def _msg_breve(m):
    return {"id": m["id"], "ts": m["ts"], "nome": m["nome"], "texto": m["texto"]}


def primeira_resposta_do_dia(msgs):
    res = []
    for nome, lista in por_grupo(msgs).items():
        ordered = sorted(lista, key=lambda x: (x["ts"], x["id"]))
        dia_actual = None
        turno_cliente = []
        i, n = 0, len(ordered)
        while i < n:
            m = ordered[i]
            if m["texto"] is None:
                i += 1
                continue
            if dia_actual != m["ts"].date():
                dia_actual = m["ts"].date()
                turno_cliente = []
            if m["tipo"] == "cliente":
                turno_cliente.append(m)
                i += 1
                continue
            if m["tipo"] == "equipe" and turno_cliente:
                turno_equipe = []
                while i < n and ordered[i]["tipo"] == "equipe" \
                        and ordered[i]["texto"] is not None \
                        and ordered[i]["ts"].date() == dia_actual:
                    turno_equipe.append(ordered[i])
                    i += 1
                res.append({
                    "grupo": nome,
                    "dia": dia_actual.strftime("%d/%m"),
                    "de": turno_cliente[-1]["ts"],
                    "resposta": turno_equipe[0]["ts"],
                    "minutos_uteis": round(tempo_util(turno_cliente[-1]["ts"], turno_equipe[0]["ts"]), 1),
                    "cliente_msgs": [_msg_breve(x) for x in turno_cliente],
                    "equipe_msgs": [_msg_breve(x) for x in turno_equipe],
                })
                turno_cliente = []
                continue
            i += 1
    return sorted(res, key=lambda x: x["dia"], reverse=True)


def histograma_faixas(tempos, meta_min):
    faixas = [
        ("< 5 min", 0, 5),
        ("5–15 min", 5, 15),
        ("15–30 min", 15, 30),
        ("30 min–1h", 30, 60),
        ("1–2h", 60, 120),
        ("2–4h", 120, 240),
        ("4–8h", 240, 480),
        ("8–24h", 480, 1440),
        ("> 24h", 1440, None),
    ]
    total = len(tempos) or 1
    out = []
    for label, lo, hi in faixas:
        if hi is None:
            n = sum(1 for t in tempos if t >= lo)
        else:
            n = sum(1 for t in tempos if lo <= t < hi)
        if hi is not None and hi <= meta_min:
            cor = "green"
        elif lo >= meta_min:
            cor = "red"
        else:
            cor = "amber"
        out.append({"label": label, "n": n, "pct": round(n / total * 100, 1), "cor": cor})
    return out


def ultima_atividade(msgs):
    por_g = {}
    for m in msgs:
        cur = por_g.get(m["grupo"])
        if cur is None or m["ts"] > cur["ts"]:
            por_g[m["grupo"]] = m
    return [
        {"grupo": nome, "ts": m["ts"], "nome": m["nome"]}
        for nome, m in sorted(por_g.items(), key=lambda x: x[1]["ts"], reverse=True)
    ]


def _status_grupo(msgs_g, dias_ambos, dias_sem_eq, dias_sem_cl, limite):
    if msgs_g == 0:
        return "nunca"
    if dias_ambos is not None and dias_ambos >= limite:
        return "inativo"
    if dias_sem_cl is None:
        return "semi_cliente"
    if dias_sem_eq is None:
        return "semi_equipe"
    if dias_sem_cl >= limite:
        return "semi_cliente"
    if dias_sem_eq >= limite:
        return "semi_equipe"
    return "ativo"


def status_grupos(msgs, grupos_registro, limite):
    fim = max((m["ts"] for m in msgs), default=None)
    por_g = por_grupo(msgs)
    out = []

    def dias(ts):
        if ts is None or fim is None:
            return None
        return round((fim - ts).total_seconds() / 86400.0, 1)

    for g in grupos_registro:
        lista = por_g.get(g["name"], [])
        ult_ambos = ult_equipe = ult_cliente = None
        for m in lista:
            if ult_ambos is None or m["ts"] > ult_ambos:
                ult_ambos = m["ts"]
            if m["tipo"] == "equipe" and (ult_equipe is None or m["ts"] > ult_equipe):
                ult_equipe = m["ts"]
            if m["tipo"] == "cliente" and (ult_cliente is None or m["ts"] > ult_cliente):
                ult_cliente = m["ts"]
        dias_ambos = dias(ult_ambos)
        dias_sem_eq = dias(ult_equipe)
        dias_sem_cl = dias(ult_cliente)
        out.append({
            "nome": g["name"],
            "lid": g["lid"],
            "msgs": len(lista),
            "ult_ambos": ult_ambos,
            "dias_ambos": dias_ambos,
            "ult_equipe": ult_equipe,
            "dias_sem_equipe": dias_sem_eq,
            "ult_cliente": ult_cliente,
            "dias_sem_cliente": dias_sem_cl,
            "status": _status_grupo(len(lista), dias_ambos, dias_sem_eq, dias_sem_cl, limite),
        })

    out.sort(key=lambda x: (0 if x["msgs"] == 0 else 1, -(x["dias_ambos"] or 0)))
    return out


def concentracao(msgs):
    out = {}
    for nome, lista in por_grupo(msgs).items():
        cont = {}
        for m in lista:
            cont[m["nome"]] = cont.get(m["nome"], 0) + 1
        top_nome, top_val = max(cont.items(), key=lambda x: x[1])
        out[nome] = {
            "top_remetente": top_nome,
            "top_pct": round(top_val / len(lista) * 100, 1),
            "total": len(lista),
        }
    return out


def _tempos_autor(msgs, chave, valor):
    tempos, sem = [], 0
    alvo = None
    for m in msgs:
        if m[chave] == valor:
            alvo = "equipe" if m["tipo"] == "cliente" else "cliente"
            break
    if alvo is None:
        return tempos, sem
    for glista in por_grupo(msgs).values():
        ordered = sorted(glista, key=lambda x: (x["ts"], x["id"]))
        n = len(ordered)
        # TS da próxima mensagem (com texto) do lado alvo após cada posição.
        prox = [None] * n
        seguinte = None
        for i in range(n - 1, -1, -1):
            prox[i] = seguinte
            if ordered[i]["tipo"] == alvo and ordered[i]["texto"] is not None:
                seguinte = ordered[i]["ts"]
        for i, m in enumerate(ordered):
            if m[chave] != valor or m["texto"] is None:
                continue
            if prox[i] is not None:
                tempos.append(tempo_util(m["ts"], prox[i]))
            else:
                sem += 1
    return tempos, sem


def por_remetente(msgs):
    by_lid = {}
    for m in msgs:
        d = by_lid.setdefault(m["lid"], {
            "nome": m["nome"],
            "tipo": m["tipo"],
            "papel": m["papel"],
            "msgs": 0,
            "grupos": set(),
        })
        d["msgs"] += 1
        d["grupos"].add(m["grupo"])
    result = []
    for lid, d in by_lid.items():
        tempos, _ = _tempos_autor(msgs, "lid", lid)
        r = sla_resumo(tempos)
        result.append({
            "lid": lid,
            "nome": d["nome"],
            "tipo": d["tipo"],
            "papel": d["papel"],
            "msgs": d["msgs"],
            "grupos": len(d["grupos"]),
            "sla_media": r["media"],
            "sla_p50": r["p50"],
            "sla_p90": r["p90"],
            "sla_n": r["n"],
        })
    return sorted(result, key=lambda x: -x["msgs"])


def engajamento_por_papel(msgs):
    total = len(msgs) or 1
    cont = {}
    for m in msgs:
        if m["papel"]:
            d = cont.setdefault(m["papel"], {"tipo": m["tipo"], "msgs": 0, "grupos": set()})
            d["msgs"] += 1
            d["grupos"].add(m["grupo"])
    out = []
    for papel, d in cont.items():
        tempos, sem = _tempos_autor(msgs, "papel", papel)
        r = sla_resumo(tempos)
        out.append({
            "papel": papel,
            "tipo": d["tipo"],
            "msgs": d["msgs"],
            "grupos": len(d["grupos"]),
            "pct_volume": round(d["msgs"] / total * 100, 1),
            "taxa_resposta": _taxa(tempos, sem),
            "sla_media": r["media"],
            "sla_p50": r["p50"],
            "sla_p90": r["p90"],
            "sem_resposta": sem,
        })
    return sorted(out, key=lambda x: -x["msgs"])


def pessoas_por_papel(msgs):
    cont = {}
    for m in msgs:
        if m["papel"]:
            cont.setdefault(m["papel"], set()).add(m["nome"])
    return {p: sorted(nomes) for p, nomes in cont.items()}


def engajamento_por_pessoa_cliente(msgs):
    total = len(msgs) or 1
    by_nome = {}
    for m in msgs:
        if m["tipo"] != "cliente" or not m["papel"]:
            continue
        d = by_nome.setdefault(m["nome"], {
            "nome": m["nome"],
            "papel": m["papel"],
            "msgs": 0,
            "grupos": set(),
        })
        d["msgs"] += 1
        d["grupos"].add(m["grupo"])
    out = []
    for nome, d in by_nome.items():
        tempos, sem = _tempos_autor(msgs, "nome", nome)
        r = sla_resumo(tempos)
        out.append({
            "nome": d["nome"],
            "papel": d["papel"],
            "msgs": d["msgs"],
            "pct_volume": round(d["msgs"] / total * 100, 1),
            "grupos": len(d["grupos"]),
            "taxa_resposta": _taxa(tempos, sem),
            "sla_media": r["media"],
            "sla_p50": r["p50"],
            "sla_p90": r["p90"],
            "sem_resposta": sem,
        })
    return sorted(out, key=lambda x: -x["msgs"])


def clientes_em_risco(msgs, limite):
    """Clientes mapeados que enviaram mensagens mas estão sem contato há
    'limite' dias ou mais (ou nunca responderam — clientes inativos)."""
    fim = max((m["ts"] for m in msgs), default=None)
    base = {c["nome"]: c for c in engajamento_por_pessoa_cliente(msgs)}
    inativos = {c["nome"] for c in clientes_inativos(msgs)}
    ultimo = {}
    for m in msgs:
        if m["tipo"] != "cliente" or not m["papel"]:
            continue
        if m["nome"] not in ultimo or m["ts"] > ultimo[m["nome"]]:
            ultimo[m["nome"]] = m["ts"]
    out = []
    for nome, d in base.items():
        ult_ts = ultimo.get(nome)
        dias = round((fim - ult_ts).total_seconds() / 86400.0, 1) if (fim and ult_ts) else None
        sem_contato = dias is not None and dias >= limite
        nunca_respondeu = nome in inativos
        if not (sem_contato or nunca_respondeu):
            continue
        out.append({
            "nome": nome,
            "papel": d["papel"],
            "grupos": d["grupos"],
            "msgs": d["msgs"],
            "taxa_resposta": d["taxa_resposta"],
            "dias_sem_contato": dias,
            "nunca_respondeu": nunca_respondeu,
        })
    return sorted(
        out,
        key=lambda x: (x["dias_sem_contato"] if x["dias_sem_contato"] is not None else 1e9),
        reverse=True,
    )


def clientes_inativos(msgs):
    ativos = set()
    clientes = {}
    for glista in por_grupo(msgs).values():
        ordered = sorted(glista, key=lambda x: (x["ts"], x["id"]))
        houve_equipe = False
        for m in ordered:
            if m["tipo"] == "equipe" and m["texto"] is not None:
                houve_equipe = True
            elif m["tipo"] == "cliente":
                d = clientes.setdefault(m["lid"], {
                    "nome": m["nome"],
                    "papel": m["papel"],
                    "msgs": 0,
                    "grupos": set(),
                })
                d["msgs"] += 1
                d["grupos"].add(m["grupo"])
                if houve_equipe and m["texto"] is not None:
                    ativos.add(m["lid"])
    return [
        {"nome": d["nome"], "papel": d["papel"], "msgs": d["msgs"], "grupos": len(d["grupos"])}
        for lid, d in sorted(clientes.items(), key=lambda x: -x[1]["msgs"])
        if lid not in ativos
    ]


def historico(msgs):
    return [
        {
            "id": m["id"],
            "nome": m["nome"],
            "tipo": m["tipo"],
            "grupo": m["grupo"],
            "ts": m["ts"],
            "resumo": (m["texto"] or "")[:90],
        }
        for m in msgs
    ]