import csv
import io
import json
import time
from datetime import datetime

from flask import Response, jsonify, redirect, render_template, request, session, url_for

from . import analise, autores, churn, config
from . import bp
from .db import get_grupos, get_mensagens

FILTER_KEYS = ("grupo", "dias", "tipo", "papel", "de", "ate")
PER_PAGE = 50


def _filtros():
    args = request.args
    if args.get("limpar"):
        session.pop("dg_filtros", None)
        return {}
    if any(k in args for k in FILTER_KEYS):
        novo = {}
        for k in FILTER_KEYS:
            v = args.get(k)
            novo[k] = int(v) if (k == "dias" and v) else (v or None)
        session["dg_filtros"] = novo
        return novo
    return session.get("dg_filtros", {}) or {}


_carregar_cache = {}
_CARREGAR_TTL = 30


def _carregar(filtros):
    chave = tuple(sorted((k, str(v)) for k, v in (filtros or {}).items()))
    agora = time.time()
    hit = _carregar_cache.get(chave)
    if hit and agora - hit[0] < _CARREGAR_TTL:
        return hit[1]

    msgs = churn.filtrar_msgs(analise.enriquecer(get_mensagens()))
    de = filtros.get("de")
    if de:
        d0 = datetime.strptime(de, "%Y-%m-%d")
        msgs = [m for m in msgs if m["ts"] >= d0]
    ate = filtros.get("ate")
    if ate:
        d1 = datetime.strptime(ate, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        msgs = [m for m in msgs if m["ts"] <= d1]
    dias = filtros.get("dias")
    if dias and msgs:
        fim = max(m["ts"] for m in msgs)
        msgs = [m for m in msgs if (fim - m["ts"]).days < dias]
    grupo = filtros.get("grupo")
    if grupo:
        msgs = [m for m in msgs if m["grupo"] == grupo]
    tipo = filtros.get("tipo")
    if tipo and tipo != "todos":
        msgs = [m for m in msgs if m["tipo"] == tipo]
    papel = filtros.get("papel")
    if papel:
        msgs = [m for m in msgs if m["papel"] == papel]

    _carregar_cache[chave] = (agora, msgs)
    return msgs


def _contexto(msgs, page):
    registro = churn.filtrar_registro(get_grupos())
    nomes = sorted({m["grupo"] for m in msgs if m["grupo"]} | {g["name"] for g in registro})
    return {
        "page": page,
        "f": _filtros(),
        "grupos": nomes,
        "papeis": autores.papeis_disponiveis(),
        "total_filtrado": len(msgs),
        "grupos_registro": registro,
    }


@bp.route("/")
def visao_geral():
    msgs = _carregar(_filtros())
    ctx = _contexto(msgs, "geral")
    resumo = analise.resumo_geral(msgs)
    ctx.update({
        "resumo": resumo,
        "grupos_monitorados": len(ctx["grupos_registro"]),
        "grupos_ativos": resumo["grupos"] if resumo else 0,
        "serie_dia": analise.serie(msgs, "dia"),
        "serie_semana": analise.serie(msgs, "semana"),
        "serie_mes": analise.serie(msgs, "mes"),
        "horas": analise.distribuicao_hora(msgs),
        "heatmap": analise.heatmap(msgs),
        "comparacao": analise.comparar_periodos(msgs),
        "top_grupos": analise.top_grupos(msgs, 12),
        "top_remetentes": analise.top_remetentes(msgs, 12),
    })
    return render_template("visao_geral.html", **ctx)


@bp.route("/sla")
def sla():
    msgs = _carregar(_filtros())
    ctx = _contexto(msgs, "sla")
    por_g = analise.sla_por_grupo(msgs)
    grafico_por_grupo = [
        [g, d["equipe_para_cliente"]["util"]["media"], d["cliente_para_equipe"]["util"]["media"]]
        for g, d in por_g.items()
    ]
    grafico_meta = [
        [g, d["equipe_para_cliente"]["pct_dentro_meta"], d["cliente_para_equipe"]["pct_dentro_meta"]]
        for g, d in por_g.items()
    ]
    m_meta = config.metas()
    ctx.update({
        "sla_geral": analise.sla_geral(msgs),
        "por_grupo": por_g,
        "grafico_por_grupo": grafico_por_grupo,
        "grafico_meta": grafico_meta,
        "hist_equipe": analise.histograma_faixas(_tempos(msgs, "cliente", "equipe"), m_meta["equipe_para_cliente_min"]),
        "hist_cliente": analise.histograma_faixas(_tempos(msgs, "equipe", "cliente"), m_meta["cliente_para_equipe_min"]),
        "sla_por_hora": analise.sla_por_hora(msgs, "cliente", "equipe"),
        "sla_dia_semana": analise.sla_por_dia_semana(msgs, "cliente", "equipe"),
        "primeiras_respostas": [_fmt_primeira(p) for p in analise.primeira_resposta_do_dia(msgs)],
        "sem_resp_equipe": _fmt_sem_resp(analise.msgs_sem_resposta(msgs, "cliente", "equipe")),
        "sem_resp_cliente": _fmt_sem_resp(analise.msgs_sem_resposta(msgs, "equipe", "cliente")),
        "metas": m_meta,
    })
    return render_template("sla.html", **ctx)


def _fmt_sem_resp(lista):
    return [
        {"id": m["id"], "grupo": m["grupo"], "nome": m["nome"], "tipo": m["tipo"],
         "papel": m["papel"], "ts": m["ts"].strftime("%d/%m/%Y %H:%M"), "texto": m["texto"]}
        for m in lista
    ]


def _fmt_msg(m):
    return {"ts": m["ts"].strftime("%d/%m %H:%M"), "nome": m["nome"], "texto": m["texto"]}


def _fmt_primeira(p):
    return {
        "grupo": p["grupo"],
        "dia": p["dia"],
        "de": p["de"].strftime("%H:%M"),
        "resposta": p["resposta"].strftime("%H:%M"),
        "minutos_uteis": p["minutos_uteis"],
        "cliente_msgs": [_fmt_msg(x) for x in p["cliente_msgs"]],
        "equipe_msgs": [_fmt_msg(x) for x in p["equipe_msgs"]],
    }


def _tempos(msgs, de, para):
    tempos = []
    for lista in analise.por_grupo(msgs).values():
        t = analise._tempos_direcao(analise._turns(lista), de, para)
        tempos.extend(t[1])
    return tempos


@bp.route("/grupos")
def grupos():
    msgs = _carregar(_filtros())
    ctx = _contexto(msgs, "grupos")
    ctx.update({
        "por_grupo": analise.sla_por_grupo(msgs),
        "concentracao": analise.concentracao(msgs),
        "por_remetente": analise.por_remetente(msgs),
    })
    return render_template("grupos.html", **ctx)


@bp.route("/diagnostico")
def diagnostico():
    msgs = _carregar(_filtros())
    q = request.args.get("q", "").strip().lower()
    busca_ativa = bool(q)
    if busca_ativa:
        msgs = [m for m in msgs if q in (m["nome"] or "").lower()
                or q in (m["grupo"] or "").lower()
                or q in (m["texto"] or "").lower()]
    pag = request.args.get("pag", type=int, default=1)
    total_paginas = max(1, (len(msgs) + PER_PAGE - 1) // PER_PAGE)
    pag = min(max(pag, 1), total_paginas)
    slice_msgs = msgs[(pag - 1) * PER_PAGE: pag * PER_PAGE]

    ult = analise.ultima_atividade(msgs)
    fim = max((m["ts"] for m in msgs), default=None)
    concentracao = analise.concentracao(msgs)
    por_grupo = analise.sla_por_grupo(msgs)
    alerts = []

    limite = config.inatividade()
    status_lista = analise.status_grupos(msgs, churn.filtrar_registro(get_grupos()), limite)
    status_por_grupo = {s["nome"]: s for s in status_lista}
    for s in status_lista:
        link = url_for("dashboard_grupos.inativos", grupo=s["nome"])
        if s["status"] == "nunca":
            alerts.append(
                {"nivel": "danger", "tipo": "Inatividade", "item": s["nome"],
                 "texto": "Grupo monitorado sem nenhuma mensagem no período (nunca ativo).", "link": link}
            )
        elif s["status"] == "inativo":
            alerts.append(
                {"nivel": "danger", "tipo": "Inatividade", "item": s["nome"],
                 "texto": f"Sem interação de ambos os lados há {s['dias_ambos']} dias.", "link": link}
            )
        elif s["status"] == "semi_cliente":
            t = f"há {s['dias_sem_cliente']} dias" if s["dias_sem_cliente"] is not None else "no período"
            alerts.append(
                {"nivel": "warning", "tipo": "Inatividade", "item": s["nome"],
                 "texto": f"Cliente sem interagir {t}.", "link": link}
            )
        elif s["status"] == "semi_equipe":
            t = f"há {s['dias_sem_equipe']} dias" if s["dias_sem_equipe"] is not None else "no período"
            alerts.append(
                {"nivel": "warning", "tipo": "Inatividade", "item": s["nome"],
                 "texto": f"Equipe sem interagir {t}.", "link": link}
            )
    for g, c in concentracao.items():
        if c["top_pct"] > 50:
            alerts.append(
                {"nivel": "warning", "tipo": "Concentração", "item": g,
                 "texto": f"{c['top_remetente']} concentra {c['top_pct']}% das mensagens.",
                 "link": url_for("dashboard_grupos.grupos")}
            )
    for g, d in por_grupo.items():
        sem_equipe = d["equipe_para_cliente"]["sem_resposta"]
        if sem_equipe:
            alerts.append(
                {"nivel": "warning", "tipo": "Sem resposta", "item": g,
                 "texto": f"{sem_equipe} mensagem(ns) de cliente sem resposta da equipe.",
                 "link": url_for("dashboard_grupos.sla")}
            )
        if d["gaps"]["max"] and d["gaps"]["max"] >= 720:
            alerts.append(
                {"nivel": "danger", "tipo": "Silêncio", "item": g,
                 "texto": f"Silêncio máximo de {int(d['gaps']['max'] // 60)}h entre mensagens.",
                 "link": url_for("dashboard_grupos.sla")}
            )
    nao_mapeados = autores.nao_mapeados(msgs)
    if nao_mapeados:
        alerts.append(
            {"nivel": "warning", "tipo": "Mapeamento", "item": f"{len(nao_mapeados)} remetente(s)",
             "texto": "Não estão no equipe.json nem no clientes.json — revisar classificação.",
             "link": url_for("dashboard_grupos.equipe_view")}
        )
    alerts.sort(key=lambda a: 0 if a["nivel"] == "danger" else 1)

    kpi_contagem = {
        "criticos": sum(1 for a in alerts if a["nivel"] == "danger"),
        "avisos": sum(1 for a in alerts if a["nivel"] == "warning"),
        "grupos_inativos": sum(1 for s in status_lista if s["status"] in ("nunca", "inativo")),
        "sem_resposta": sum(d["equipe_para_cliente"]["sem_resposta"] for d in por_grupo.values()),
        "nao_mapeados": len(nao_mapeados),
    }
    ctx = _contexto(msgs, "diagnostico")
    ctx.update({
        "ultima_atividade": ult,
        "status_por_grupo": status_por_grupo,
        "concentracao": concentracao,
        "por_grupo": por_grupo,
        "resumo": analise.resumo_geral(msgs),
        "qualidade": analise.qualidade(msgs),
        "historico": analise.historico(slice_msgs),
        "alerts": alerts,
        "kpi_contagem": kpi_contagem,
        "nao_mapeados": nao_mapeados,
        "q": q,
        "pag": pag,
        "total_paginas": total_paginas,
        "busca_ativa": busca_ativa,
    })
    return render_template("diagnostico.html", **ctx)


@bp.route("/equipe", methods=["GET", "POST"])
def equipe_view():
    msg = "Mapeamento importado com sucesso." if request.args.get("import_ok") else None
    erro = request.args.get("import_erro")
    if request.method == "POST":
        acao = request.form.get("acao")
        if acao in ("add", "add_cliente"):
            nome = request.form.get("nome", "").strip()
            papel = request.form.get("papel", "").strip()
            tipo = "cliente" if acao == "add_cliente" else request.form.get("tipo", "equipe")
            if tipo == "cliente" and not papel:
                papel = "cliente"
            if nome and papel:
                if autores.adicionar(nome, papel, tipo):
                    msg = f"'{nome}' adicionado como {tipo}."
                else:
                    msg = "Nome inválido."
        elif acao == "remove":
            nome = request.form.get("nome", "")
            if autores.remover(nome):
                msg = f"'{nome}' removido do mapeamento."
    msgs = get_mensagens()
    return render_template(
        "equipe.html",
        page="equipe",
        f=_filtros(),
        papeis=autores.papeis_disponiveis(),
        grupos=[],
        membros=autores.membros(),
        nao_mapeados=autores.nao_mapeados(msgs),
        msg=msg,
        erro=erro,
        total_filtrado=len(msgs),
    )


@bp.route("/engajamento")
def engajamento():
    msgs = _carregar(_filtros())
    ctx = _contexto(msgs, "engajamento")
    ctx.update({
        "resumo": analise.resumo_geral(msgs),
        "por_papel": analise.por_papel(msgs),
        "engajamento": analise.engajamento_por_papel(msgs),
        "pessoas_por_papel": analise.pessoas_por_papel(msgs),
        "por_pessoa_cliente": analise.engajamento_por_pessoa_cliente(msgs),
        "clientes_inativos": analise.clientes_inativos(msgs),
        "clientes_risco": analise.clientes_em_risco(msgs, config.inatividade()),
        "limite": config.inatividade(),
    })
    return render_template("engajamento.html", **ctx)


@bp.route("/inativos")
def inativos():
    msgs = _carregar(_filtros())
    ctx = _contexto(msgs, "inativos")
    limite = config.inatividade()
    status = analise.status_grupos(msgs, ctx["grupos_registro"], limite)
    if ctx["f"].get("grupo"):
        status = [s for s in status if s["nome"] == ctx["f"]["grupo"]]
    contagem = {}
    for s in status:
        contagem[s["status"]] = contagem.get(s["status"], 0) + 1
    ctx.update({
        "limite": limite,
        "status": status,
        "contagem": contagem,
        "resumo": analise.resumo_geral(msgs),
    })
    return render_template("inativos.html", **ctx)


@bp.route("/churn", methods=["GET", "POST"])
def churn_view():
    msg = None
    if request.method == "POST":
        acao = request.form.get("acao")
        nome = request.form.get("nome", "")
        lid = request.form.get("lid", "")
        if acao == "marcar":
            if churn.marcar(nome, lid):
                msg = f"'{nome}' marcado como churn (ocultado das métricas)."
        elif acao == "desmarcar":
            if churn.desmarcar(nome):
                msg = f"'{nome}' reativado nas métricas."
    msgs = analise.enriquecer(get_mensagens())
    por_g = {}
    for m in msgs:
        por_g[m["grupo"]] = por_g.get(m["grupo"], 0) + 1
    linhas = []
    for g in get_grupos():
        is_churn = churn.e_churn(g["name"])
        linhas.append({"nome": g["name"], "lid": g["lid"], "churn": is_churn,
                       "msgs": por_g.get(g["name"], 0)})
    linhas.sort(key=lambda x: (not x["churn"], x["nome"].lower()))
    total_ocultas = sum(l["msgs"] for l in linhas if l["churn"])
    return render_template(
        "churn.html",
        page="churn",
        f=_filtros(),
        papeis=autores.papeis_disponiveis(),
        grupos=[],
        linhas=linhas,
        total_churn=sum(1 for l in linhas if l["churn"]),
        total_ocultas=total_ocultas,
        msg=msg,
        total_filtrado=len(msgs),
    )


@bp.route("/config", methods=["GET", "POST"])
def config_view():
    msg = None
    erro = None
    if request.method == "POST":
        try:
            inicio = request.form.get("inicio", "08:00").strip()
            fim = request.form.get("fim", "18:00").strip()
            e2c = int(request.form.get("equipe_para_cliente_min", 60))
            c2e = int(request.form.get("cliente_para_equipe_min", 180))
            inat = int(request.form.get("inatividade_dias", 3))
            datetime.strptime(inicio, "%H:%M")
            datetime.strptime(fim, "%H:%M")
            if e2c < 1 or c2e < 1 or inat < 1:
                raise ValueError("os valores devem ser maiores que zero.")
            config.salvar({
                "atendimento": {
                    "inicio": inicio,
                    "fim": fim,
                    "dias_uteis": request.form.get("dias_uteis") == "on",
                },
                "metas": {
                    "equipe_para_cliente_min": e2c,
                    "cliente_para_equipe_min": c2e,
                },
                "inatividade_dias": inat,
            })
            msg = "Configurações salvas. As mudanças já valem no dashboard."
        except ValueError as e:
            erro = f"Valor inválido: {e}"
    return render_template(
        "config.html",
        page="config",
        f=_filtros(),
        papeis=autores.papeis_disponiveis(),
        grupos=[],
        cfg=config.atual(),
        msg=msg,
        erro=erro,
        total_filtrado=0,
    )


@bp.route("/api/metricas")
def api_metricas():
    msgs = _carregar(_filtros())
    return jsonify({
        "resumo": analise.resumo_geral(msgs),
        "sla": analise.sla_geral(msgs),
        "sla_por_grupo": analise.sla_por_grupo(msgs),
        "top_grupos": analise.top_grupos(msgs, 10),
        "top_remetentes": analise.top_remetentes(msgs, 10),
    })


@bp.route("/exportar.csv")
def exportar_csv():
    msgs = _carregar(_filtros())
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["id", "grupo", "nome", "tipo", "papel", "data", "hora", "mensagem"])
    for m in msgs:
        w.writerow([m["id"], m["grupo"], m["nome"], m["tipo"], m["papel"],
                    m["data"], m["hora"], m["texto"] or ""])
    resp = Response(out.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=mensagens.csv"
    return resp


@bp.route("/mapping/export")
def mapping_export():
    d = autores.dados()
    bundle = {"equipe": d["equipe"], "clientes": d["clientes"], "churn": churn.dados()}
    resp = Response(json.dumps(bundle, ensure_ascii=False, indent=2), mimetype="application/json")
    resp.headers["Content-Disposition"] = "attachment; filename=mapeamento_dashboard.json"
    return resp


@bp.route("/mapping/import", methods=["POST"])
def mapping_import():
    arquivo = request.files.get("arquivo")
    if not arquivo or not arquivo.filename:
        return redirect(url_for("dashboard_grupos.equipe_view", import_erro="Selecione um arquivo."))
    try:
        bundle = json.loads(arquivo.read().decode("utf-8"))
        if not isinstance(bundle, dict):
            raise ValueError("o JSON raiz deve ser um objeto.")
        autores.importar(bundle.get("equipe", {}), bundle.get("clientes", {}))
        if "churn" in bundle:
            churn.importar(bundle["churn"])
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
        return redirect(url_for("dashboard_grupos.equipe_view", import_erro=f"Arquivo inválido: {e}"))
    return redirect(url_for("dashboard_grupos.equipe_view", import_ok="1"))