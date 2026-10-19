from datetime import date, datetime

from .engine import analisar_projeto

CAMPOS_FILTRO = ["status", "impacto", "urgencia", "risco", "esforco", "ritmo"]


def _parse_data(valor):
    if not valor:
        return None
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _como_data(valor):
    if isinstance(valor, datetime):
        return valor.date()
    return valor


def _no_intervalo(projeto, de, ate):
    inicio = _como_data(projeto.get("data_inicio"))
    fim = _como_data(projeto.get("data_fim")) or _como_data(
        projeto.get("data_prevista_fim")
    )
    if inicio is None and fim is None:
        return False
    if de is not None and fim is not None and fim < de:
        return False
    if ate is not None and inicio is not None and inicio > ate:
        return False
    return True



def construir_linhas(projetos_com_etapas, cfg):
    linhas = []
    for projeto, etapas in projetos_com_etapas:
        analise = analisar_projeto(projeto, etapas, cfg)
        linhas.append({"projeto": projeto, "etapas": etapas, "analise": analise})
    return linhas


def aplicar_filtros(linhas, args):
    filtros = {campo: (args.get(campo) or None) for campo in CAMPOS_FILTRO}
    responsavel = args.get("responsavel") or None
    somente_atencao = args.get("atencao") == "1"
    busca = (args.get("q") or "").strip().lower()
    de = _parse_data(args.get("de"))
    ate = _parse_data(args.get("ate"))

    resultado = []
    for linha in linhas:
        projeto = linha["projeto"]
        analise = linha["analise"]

        if busca and busca not in (projeto.get("nome") or "").lower():
            continue
        if filtros["status"] and projeto["status"] != filtros["status"]:
            continue
        if filtros["impacto"] and projeto["impacto"] != filtros["impacto"]:
            continue
        if filtros["urgencia"] and projeto["urgencia"] != filtros["urgencia"]:
            continue
        if filtros["risco"] and projeto["risco"] != filtros["risco"]:
            continue
        if filtros["esforco"] and projeto["esforco"] != filtros["esforco"]:
            continue
        if filtros["ritmo"] and analise["saude"]["ritmo"] != filtros["ritmo"]:
            continue
        if responsavel and str(projeto.get("responsavel_id")) != str(responsavel):
            continue
        if somente_atencao and analise["intervencao"]["nivel"] == "normal":
            continue
        if (de or ate) and not _no_intervalo(projeto, de, ate):
            continue
        resultado.append(linha)
    return resultado


def ordenar_prioridade(linhas):
    return sorted(
        linhas, key=lambda linha: linha["analise"]["prioridade"]["indice"], reverse=True
    )


def agrupar_por_status(linhas, ordem):
    colunas = {status: [] for status in ordem}
    for linha in linhas:
        status = linha["projeto"]["status"]
        colunas.setdefault(status, []).append(linha)
    return colunas


def resumo_intervencao(linhas):
    intervencao = sum(1 for l in linhas if l["analise"]["intervencao"]["nivel"] == "intervencao")
    atencao = sum(1 for l in linhas if l["analise"]["intervencao"]["nivel"] == "atencao")
    return {"intervencao": intervencao, "atencao": atencao, "total": intervencao + atencao}


def chips_filtros(args, membros, endpoint):
    from flask import url_for

    from . import domain
    from .ui import data_br

    parametros = args.to_dict()
    nomes = {str(m["id"]): m["nome"] for m in membros}
    chips = []

    def adicionar(chave, rotulo):
        if parametros.get(chave):
            resto = {k: v for k, v in parametros.items() if k != chave}
            chips.append({"rotulo": rotulo, "url": url_for(endpoint, **resto)})

    adicionar("q", f'Busca: "{parametros.get("q")}"')
    adicionar(
        "responsavel",
        f'Responsável: {nomes.get(str(parametros.get("responsavel")), parametros.get("responsavel"))}',
    )
    adicionar("status", f'Status: {domain.label_status(parametros.get("status")).get("label")}')
    for campo in ("impacto", "urgencia", "risco", "esforco"):
        valor = parametros.get(campo)
        if valor:
            adicionar(
                campo,
                f'{domain.INDICADORES[campo]["label"]}: {domain.meta_indicador(campo, valor).get("label")}',
            )
    adicionar("ritmo", f'Ritmo: {domain.label_ritmo(parametros.get("ritmo")).get("label")}')
    if parametros.get("de"):
        adicionar("de", f'De: {data_br(parametros.get("de"))}')
    if parametros.get("ate"):
        adicionar("ate", f'Até: {data_br(parametros.get("ate"))}')
    adicionar("atencao", "Somente atenção")
    return chips


def _somar_meses(data, delta):
    total = data.year * 12 + (data.month - 1) + delta
    return date(total // 12, total % 12 + 1, 1)


def tendencia_mensal(linhas, meses=6):
    hoje = date.today()
    chaves = {}
    atual = _somar_meses(hoje, -(meses - 1))
    while atual <= hoje:
        chaves[atual] = {"rotulo": atual.strftime("%m/%y"), "criados": 0, "finalizados": 0}
        atual = _somar_meses(atual, 1)

    for linha in linhas:
        projeto = linha["projeto"]
        criado = _como_data(projeto.get("created_at"))
        if criado:
            mes_criado = date(criado.year, criado.month, 1)
            if mes_criado in chaves:
                chaves[mes_criado]["criados"] += 1
        if projeto.get("status") == "finalizado":
            fim = _como_data(projeto.get("data_fim")) or criado
            if fim:
                mes_fim = date(fim.year, fim.month, 1)
                if mes_fim in chaves:
                    chaves[mes_fim]["finalizados"] += 1

    meses_ordenados = [chaves[m] for m in sorted(chaves)]
    maximo = max(
        [1]
        + [v["criados"] for v in meses_ordenados]
        + [v["finalizados"] for v in meses_ordenados]
    )
    return {"meses": meses_ordenados, "max": maximo}


def contagem_por_status(linhas):
    contagem = {"fila": 0, "ativo": 0, "pausado": 0, "finalizado": 0}
    for linha in linhas:
        status = linha["projeto"]["status"]
        contagem[status] = contagem.get(status, 0) + 1
    contagem["total"] = sum(
        contagem[chave] for chave in ("fila", "ativo", "pausado", "finalizado")
    )
    return contagem


def capacidade_membros(linhas, membros, cfg):
    padrao = cfg.get("capacidade", {}).get("limite_ativo_padrao", 3)
    situacoes = {
        "acima": "vermelho",
        "cheio": "ambar",
        "proximo": "azul",
        "ok": "verde",
    }
    rotulos = {
        "acima": "Acima do limite",
        "cheio": "Em capacidade",
        "proximo": "Quase no limite",
        "ok": "OK",
    }
    resultado = []
    for membro in membros:
        ativos = sum(
            1
            for linha in linhas
            if linha["projeto"].get("status") == "ativo"
            and linha["projeto"].get("responsavel_id") == membro["id"]
        )
        limite = membro.get("capacidade")
        limite = limite if isinstance(limite, int) and limite > 0 else padrao
        if ativos > limite:
            situacao = "acima"
        elif ativos == limite and limite > 0:
            situacao = "cheio"
        elif ativos == limite - 1 and ativos > 0:
            situacao = "proximo"
        else:
            situacao = "ok"
        resultado.append(
            {
                "id": membro["id"],
                "nome": membro["nome"],
                "ativos": ativos,
                "limite": limite,
                "situacao": situacao,
                "cor": situacoes[situacao],
                "rotulo": rotulos[situacao],
            }
        )
    return resultado


def mapa_capacidade(cfg):
    from . import db

    linhas = construir_linhas(db.projetos_com_etapas(), cfg)
    membros = db.listar_membros()
    return {
        capacidade["id"]: capacidade
        for capacidade in capacidade_membros(linhas, membros, cfg)
    }


def mapa_tempos(projeto_ids):
    from . import db

    bruto = db.tempos_resumo_por_projeto(projeto_ids)
    mapa = {}
    for projeto_id, info in bruto.items():
        mapa[projeto_id] = {
            "total": info["total"],
            "inicios": ",".join(
                str(int(inicio.timestamp() * 1000)) for inicio in info["ativas"]
            ),
            "ativo": bool(info["ativas"]),
        }
    return mapa



ORDEM_COLUNAS = ["fila", "ativo", "pausado", "finalizado"]


def contexto_lista_projetos(args):
    from flask import url_for

    from . import db
    from .config import get_config

    cfg = get_config()
    linhas = construir_linhas(db.projetos_com_etapas(), cfg)
    filtradas = aplicar_filtros(linhas, args)
    ordenadas = ordenar_prioridade(filtradas)

    aba = args.get("aba", "geral")
    parametros = args.to_dict()
    parametros.pop("aba", None)
    membros = db.listar_membros()
    colunas = agrupar_por_status(ordenadas, ORDEM_COLUNAS)
    colunas["fila"].sort(
        key=lambda linha: (linha["projeto"].get("ordem") or 0, linha["projeto"]["id"])
    )
    url_geral = url_for("painel_tech.projetos_listar", **parametros)
    url_kanban = url_for("painel_tech.projetos_listar", aba="kanban", **parametros)
    return {
        "linhas": ordenadas,
        "total": len(linhas),
        "membros": membros,
        "contagem": db.contar_por_status(),
        "args": args,
        "aba": aba,
        "url_geral": url_geral,
        "url_kanban": url_kanban,
        "url_limpar": url_kanban if aba == "kanban" else url_geral,
        "url_export": url_for("painel_tech.projetos_export", **parametros),
        "chips": chips_filtros(args, membros, "painel_tech.projetos_listar"),
        "tempos": mapa_tempos([linha["projeto"]["id"] for linha in ordenadas]),
        "colunas": colunas,
        "ordem_colunas": ORDEM_COLUNAS,
    }


def contexto_projeto(projeto_id):
    from . import db
    from .config import get_config

    projeto = db.obter_projeto(projeto_id)
    if not projeto:
        return None
    etapas = db.listar_etapas(projeto_id)
    concluidas = {etapa["id"] for etapa in etapas if etapa.get("status") == "concluida"}
    for etapa in etapas:
        etapa["dep_pendente"] = bool(
            etapa.get("dependencia_id")
            and etapa.get("status") != "concluida"
            and etapa["dependencia_id"] not in concluidas
        )
    analise = analisar_projeto(projeto, etapas, get_config())
    comentarios = db.listar_comentarios(projeto_id=projeto_id, todas=True)
    comentarios_projeto = [c for c in comentarios if not c.get("etapa_id")]
    comentarios_etapa = {}
    for comentario in comentarios:
        if comentario.get("etapa_id"):
            comentarios_etapa.setdefault(comentario["etapa_id"], []).append(comentario)
    resumo_checklist = {
        "concluidas": sum(1 for e in etapas if e.get("status") == "concluida"),
        "total": len(etapas),
        "vencidas": analise["saude"]["etapas_vencidas"],
        "bloqueadas": sum(1 for e in etapas if e.get("bloqueada") or e.get("dep_pendente")),
    }
    tempo = mapa_tempos([projeto_id]).get(
        projeto_id, {"total": 0, "inicios": "", "ativo": False}
    )
    return {
        "projeto": projeto,
        "etapas": etapas,
        "analise": analise,
        "resumo_checklist": resumo_checklist,
        "tempo": tempo,
        "membros": db.listar_membros(),
        "eventos": db.listar_eventos(projeto_id),
        "comentarios_projeto": comentarios_projeto,
        "comentarios_etapa": comentarios_etapa,
    }


def quer_fragmento():
    from flask import request

    return request.headers.get("HX-Request") == "true"


def usuario_atual():
    from flask import request, session

    usuario = session.get("usuario") if session is not None else None
    if usuario:
        return usuario
    nome = request.headers.get("X-Usuario")
    if nome:
        return {"id": None, "nome": nome}
    return {"id": None, "nome": None}


def registrar_evento(projeto_id, tipo, descricao=None, etapa_id=None, payload=None):
    from . import db

    autor = usuario_atual()
    db.registrar_evento(
        projeto_id,
        tipo,
        descricao=descricao,
        etapa_id=etapa_id,
        autor_id=autor.get("id"),
        autor_nome=autor.get("nome"),
        payload=payload,
    )


def enfileirar_toast(mensagem, tipo="ok"):
    from flask import g

    lista = getattr(g, "toasts", None)
    if lista is None:
        lista = []
        g.toasts = lista
    lista.append({"mensagem": mensagem, "tipo": tipo})


def anexar_toasts(resposta):
    import json

    from flask import g, make_response

    resposta = make_response(resposta)
    toasts = getattr(g, "toasts", None)
    if toasts:
        resposta.headers["HX-Trigger"] = json.dumps({"toast": toasts})
    return resposta


def resposta_projeto(projeto_id):
    from flask import abort, redirect, render_template, url_for

    if quer_fragmento():
        contexto = contexto_projeto(projeto_id)
        if contexto is None:
            abort(404)
        return anexar_toasts(
            render_template("painel_tech/partials/_projeto_estado.html", **contexto)
        )
    return redirect(url_for("painel_tech.projeto_detalhe", projeto_id=projeto_id))
