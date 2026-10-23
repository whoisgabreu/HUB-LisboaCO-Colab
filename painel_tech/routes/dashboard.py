from flask import abort, render_template, request, url_for

from .. import bp, db, view_utils
from ..config import get_config
from ..domain import INDICADORES, INTERVENCAO, PRIORIDADE, RITMO, STATUS


def _linhas_filtradas(cfg):
    linhas = view_utils.construir_linhas(db.projetos_com_etapas(), cfg)
    return linhas, view_utils.aplicar_filtros(linhas, request.args)


def _dados_metricas(linhas, membros, cfg):
    """Monta apenas dados de apresentação para os gráficos da página."""
    from datetime import date, datetime, timedelta

    def como_data(valor):
        if isinstance(valor, datetime):
            return valor.date()
        if isinstance(valor, date):
            return valor
        if isinstance(valor, str):
            try:
                return date.fromisoformat(valor[:10])
            except ValueError:
                return None
        return None

    def faixa_progresso(progresso):
        if progresso <= 0:
            return "0%"
        if progresso <= 25:
            return "1–25%"
        if progresso <= 50:
            return "26–50%"
        if progresso <= 75:
            return "51–75%"
        if progresso < 100:
            return "76–99%"
        return "100%"

    hoje = date.today()
    limite_proximo = hoje + timedelta(days=7)
    contagem = view_utils.contagem_por_status(linhas)
    membros_por_id = {membro["id"]: membro for membro in membros}
    saude = {chave: 0 for chave in ("normal", "atencao", "intervencao")}
    prioridades = {chave: 0 for chave in ("critica", "alta", "media", "baixa")}
    registros = []

    for linha in linhas:
        projeto = linha["projeto"]
        analise = linha["analise"]
        nivel_saude = analise["intervencao"]["nivel"]
        nivel_prioridade = analise["prioridade"]["nivel"]
        saude[nivel_saude] = saude.get(nivel_saude, 0) + 1
        prioridades[nivel_prioridade] = prioridades.get(nivel_prioridade, 0) + 1

        membro = membros_por_id.get(projeto.get("responsavel_id"))
        responsavel = (
            (membro or {}).get("nome")
            or projeto.get("responsavel_nome")
            or "Sem responsável"
        )
        impacto = INDICADORES["impacto"]["opcoes"].get(projeto.get("impacto"), {})
        urgencia = INDICADORES["urgencia"]["opcoes"].get(projeto.get("urgencia"), {})
        risco = INDICADORES["risco"]["opcoes"].get(projeto.get("risco"), {})
        esforco = INDICADORES["esforco"]["opcoes"].get(projeto.get("esforco"), {})
        ritmo = RITMO.get(analise["saude"]["ritmo"], {})
        saude_projeto = analise["saude"]
        progresso = saude_projeto["progresso_pct"]
        prazo = como_data(projeto.get("data_prevista_fim"))
        criado_em = como_data(projeto.get("created_at"))
        status = projeto.get("status")
        if prazo is None:
            estado_prazo = "Sem prazo"
        elif status == "finalizado":
            estado_prazo = "Finalizado"
        elif prazo < hoje:
            estado_prazo = "Atrasado"
        elif prazo <= limite_proximo:
            estado_prazo = "Vence em até 7 dias"
        else:
            estado_prazo = "No prazo"

        concluidas_ids = {
            etapa.get("id")
            for etapa in linha["etapas"]
            if etapa.get("status") == "concluida"
        }
        etapas_bloqueadas = sum(
            1
            for etapa in linha["etapas"]
            if etapa.get("bloqueada")
            or (
                etapa.get("dependencia_id")
                and etapa.get("status") != "concluida"
                and etapa.get("dependencia_id") not in concluidas_ids
            )
        )
        etapas_vencidas = saude_projeto["etapas_vencidas"]

        registros.append(
            {
                "name": projeto.get("nome") or "Projeto sem nome",
                "status": STATUS.get(projeto.get("status"), {}).get(
                    "label", projeto.get("status") or "Sem status"
                ),
                "owner": responsavel,
                "impact": impacto.get("label", projeto.get("impacto") or "Sem impacto"),
                "impactLevel": impacto.get("nivel", 0),
                "urgency": urgencia.get("label", projeto.get("urgencia") or "Sem urgência"),
                "risk": risco.get("label", projeto.get("risco") or "Sem risco"),
                "effort": esforco.get("label", projeto.get("esforco") or "Sem esforço"),
                "effortLevel": esforco.get("nivel", 0),
                "rhythm": ritmo.get("label", analise["saude"]["ritmo"]),
                "priority": analise["prioridade"]["label"],
                "priorityIndex": analise["prioridade"]["indice"],
                "health": analise["intervencao"]["label"],
                "intervention": analise["intervencao"]["label"],
                "progress": progresso,
                "progressBand": faixa_progresso(progresso),
                "assignment": "Com responsável" if projeto.get("responsavel_id") else "Sem responsável",
                "deadlineState": estado_prazo,
                "overdueState": "Com etapas vencidas" if etapas_vencidas else "Sem etapas vencidas",
                "blockageState": "Com bloqueio" if etapas_bloqueadas else "Sem bloqueio",
                "createdMonth": criado_em.strftime("%m/%Y") if criado_em else "Sem data",
                "createdMonthKey": criado_em.strftime("%Y-%m") if criado_em else "9999-99",
                "stepsTotal": saude_projeto["total"],
                "stepsCompleted": saude_projeto["concluidas"],
                "stepsPending": max(saude_projeto["total"] - saude_projeto["concluidas"], 0),
                "stepsOverdue": etapas_vencidas,
                "stepsBlocked": etapas_bloqueadas,
            }
        )

    capacidades = view_utils.capacidade_membros(linhas, membros, cfg)
    ativos = [linha for linha in linhas if linha["projeto"]["status"] == "ativo"]
    progresso_medio = (
        round(
            sum(linha["analise"]["saude"]["progresso_pct"] for linha in ativos)
            / len(ativos)
        )
        if ativos
        else 0
    )
    total = contagem["total"]
    tendencia = view_utils.tendencia_mensal(linhas, 6)

    return {
        "summary": {
            "total": total,
            "active": contagem["ativo"],
            "averageProgress": progresso_medio,
            "attention": saude.get("atencao", 0) + saude.get("intervencao", 0),
            "completionRate": round(contagem["finalizado"] / total * 100) if total else 0,
        },
        "status": [
            {
                "key": chave,
                "label": meta["label"],
                "value": contagem.get(chave, 0),
            }
            for chave, meta in STATUS.items()
        ],
        "health": [
            {
                "key": chave,
                "label": INTERVENCAO[chave]["label"],
                "value": saude.get(chave, 0),
            }
            for chave in ("normal", "atencao", "intervencao")
        ],
        "priority": [
            {
                "key": chave,
                "label": PRIORIDADE[chave]["label"],
                "value": prioridades.get(chave, 0),
            }
            for chave in ("critica", "alta", "media", "baixa")
        ],
        "activeProjects": [
            {
                "name": linha["projeto"]["nome"],
                "value": linha["analise"]["saude"]["progresso_pct"],
                "rhythm": RITMO.get(linha["analise"]["saude"]["ritmo"], {}).get(
                    "label", linha["analise"]["saude"]["ritmo"]
                ),
            }
            for linha in view_utils.ordenar_prioridade(ativos)
        ],
        "trend": [
            {
                "label": mes["rotulo"],
                "created": mes["criados"],
                "finished": mes["finalizados"],
            }
            for mes in tendencia["meses"]
        ],
        "workload": [
            {
                "name": capacidade["nome"],
                "active": capacidade["ativos"],
                "limit": capacidade["limite"],
                "state": capacidade["situacao"],
            }
            for capacidade in capacidades
        ],
        "rows": registros,
    }


@bp.route("/")
def dashboard():
    cfg = get_config()
    linhas, filtradas = _linhas_filtradas(cfg)
    operacionais = [
        linha for linha in filtradas if linha["projeto"].get("status") != "finalizado"
    ]
    atencao = view_utils.ordenar_prioridade(
        [
            linha
            for linha in operacionais
            if linha["analise"]["intervencao"]["nivel"] != "normal"
        ]
    )
    membros = db.listar_membros()
    return render_template(
        "painel_tech/dashboard.html",
        contagem=view_utils.contagem_por_status(operacionais),
        atencao=atencao,
        linhas=view_utils.ordenar_prioridade(operacionais),
        membros=membros,
        chips=view_utils.chips_filtros(request.args, membros, "painel_tech.dashboard"),
        url_limpar=url_for("painel_tech.dashboard"),
        args=request.args,
    )


@bp.route("/capacidade")
def capacidade_pagina():
    cfg = get_config()
    linhas = view_utils.construir_linhas(db.projetos_com_etapas(), cfg)
    membros = db.listar_membros()
    return render_template(
        "painel_tech/capacidade.html",
        capacidade=view_utils.capacidade_membros(linhas, membros, cfg),
    )


@bp.route("/capacidade/<int:membro_id>")
def capacidade_membro(membro_id):
    membros = db.listar_membros()
    membro = next((m for m in membros if m["id"] == membro_id), None)
    if not membro:
        abort(404)
    cfg = get_config()
    linhas = view_utils.construir_linhas(db.projetos_com_etapas(), cfg)
    do_membro = [
        linha
        for linha in linhas
        if linha["projeto"].get("responsavel_id") == membro_id
        and linha["projeto"].get("status") != "finalizado"
    ]
    capacidades = {
        cap["id"]: cap
        for cap in view_utils.capacidade_membros(linhas, membros, cfg)
    }
    return render_template(
        "painel_tech/capacidade_membro.html",
        membro=membro,
        cap=capacidades.get(membro_id),
        linhas=view_utils.ordenar_prioridade(do_membro),
    )


@bp.route("/metricas")
def metricas_pagina():
    cfg = get_config()
    linhas, filtradas = _linhas_filtradas(cfg)
    ativos = view_utils.ordenar_prioridade(
        [linha for linha in filtradas if linha["projeto"]["status"] == "ativo"]
    )
    membros = db.listar_membros()
    return render_template(
        "painel_tech/metricas.html",
        contagem=view_utils.contagem_por_status(filtradas),
        ativos=ativos,
        tendencia=view_utils.tendencia_mensal(filtradas, 6),
        metricas=_dados_metricas(filtradas, membros, cfg),
        membros=membros,
        chips=view_utils.chips_filtros(request.args, membros, "painel_tech.metricas_pagina"),
        url_limpar=url_for("painel_tech.metricas_pagina"),
        args=request.args,
    )
