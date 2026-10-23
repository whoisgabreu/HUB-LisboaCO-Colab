import csv
import io
from datetime import date

from flask import (
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from .. import bp, db, kanban_layout, view_utils
from ..config import get_config
from ..domain import (
    INDICADORES,
    STATUS,
    label_intervencao,
    label_ritmo,
    label_status,
    meta_indicador,
)
from ..ui import tempo_br


def _dados_projeto(form):
    return {
        "nome": form.get("nome", "").strip(),
        "descricao": form.get("descricao", "").strip(),
        "status": form.get("status", "fila"),
        "responsavel_id": form.get("responsavel_id") or None,
        "impacto": form.get("impacto", "medio"),
        "urgencia": form.get("urgencia", "media"),
        "risco": form.get("risco", "medio"),
        "esforco": form.get("esforco", "medio"),
        "ritmo_manual": form.get("ritmo_manual") or None,
        "ritmo_justificativa": form.get("ritmo_justificativa", "").strip() or None,
        "data_inicio": form.get("data_inicio") or None,
        "data_prevista_fim": form.get("data_prevista_fim") or None,
        "data_fim": form.get("data_fim") or None,
    }


def _aplicar_status(projeto_id, novo_status):
    from datetime import date

    dados = {"status": novo_status, "data_fim": None}
    if novo_status == "finalizado":
        dados["data_fim"] = date.today().isoformat()
    if novo_status == "fila":
        dados["ordem"] = db.proxima_ordem_projeto()
    db.atualizar_projeto(projeto_id, dados)
    if novo_status == "finalizado":
        db.pausar_sessao(projeto_id)
    rotulo = STATUS.get(novo_status, {}).get("label", novo_status)
    view_utils.registrar_evento(projeto_id, "status_alterado", f"Status alterado para {rotulo}")


def _contexto_kanban():
    return kanban_layout.aplicar_contexto(
        view_utils.contexto_lista_projetos(request.args)
    )


@bp.route("/projetos")
def projetos_listar():
    contexto = view_utils.contexto_lista_projetos(request.args)
    if contexto["aba"] == "kanban":
        contexto = kanban_layout.aplicar_contexto(contexto)
        return render_template("painel_tech/projetos_kanban.html", **contexto)
    return render_template("painel_tech/projetos.html", **contexto)


@bp.route("/projetos/export.csv")
def projetos_export():
    contexto = view_utils.contexto_lista_projetos(request.args)
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";")
    escritor.writerow(
        [
            "Projeto",
            "Status",
            "Responsável",
            INDICADORES["impacto"]["label"],
            INDICADORES["urgencia"]["label"],
            INDICADORES["risco"]["label"],
            INDICADORES["esforco"]["label"],
            "Prioridade",
            "Índice",
            "Ritmo",
            "Progresso (%)",
            "Intervenção",
        ]
    )
    for linha in contexto["linhas"]:
        projeto = linha["projeto"]
        analise = linha["analise"]
        escritor.writerow(
            [
                projeto["nome"],
                label_status(projeto["status"])["label"],
                projeto.get("responsavel_nome") or "",
                meta_indicador("impacto", projeto["impacto"])["label"],
                meta_indicador("urgencia", projeto["urgencia"])["label"],
                meta_indicador("risco", projeto["risco"])["label"],
                meta_indicador("esforco", projeto["esforco"])["label"],
                analise["prioridade"]["label"],
                analise["prioridade"]["indice"],
                label_ritmo(analise["saude"]["ritmo"])["label"],
                analise["saude"]["progresso_pct"],
                label_intervencao(analise["intervencao"]["nivel"])["label"],
            ]
        )
    conteudo = "\ufeff" + buffer.getvalue()
    return Response(
        conteudo,
        content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=projetos.csv"},
    )


@bp.route("/projetos/novo", methods=["GET", "POST"])
def projetos_novo():
    capacidades_por_membro = view_utils.mapa_capacidade(get_config())
    if request.method == "POST":
        dados = _dados_projeto(request.form)
        if not dados["nome"]:
            flash("Informe o nome do projeto.", "erro")
            return render_template(
                "painel_tech/projeto_form.html",
                projeto=dados,
                membros=db.listar_membros(),
                capacidades_por_membro=capacidades_por_membro,
                modo="novo",
            )
        criado = db.criar_projeto(dados)
        view_utils.registrar_evento(
            criado["id"], "projeto_criado", f"Projeto '{criado['nome']}' criado"
        )
        flash("Projeto criado com sucesso.", "ok")
        return redirect(url_for("painel_tech.projeto_detalhe", projeto_id=criado["id"]))
    return render_template(
        "painel_tech/projeto_form.html",
        projeto={},
        membros=db.listar_membros(),
        capacidades_por_membro=capacidades_por_membro,
        modo="novo",
    )


@bp.route("/projetos/<int:projeto_id>")
def projeto_detalhe(projeto_id):
    contexto = view_utils.contexto_projeto(projeto_id)
    if contexto is None:
        abort(404)
    return render_template("painel_tech/projeto_detalhe.html", **contexto)


@bp.route("/projetos/<int:projeto_id>/editar", methods=["GET", "POST"])
def projeto_editar(projeto_id):
    projeto = db.obter_projeto(projeto_id)
    if not projeto:
        abort(404)
    capacidades_por_membro = view_utils.mapa_capacidade(get_config())
    if request.method == "POST":
        dados = _dados_projeto(request.form)
        if not dados["nome"]:
            flash("Informe o nome do projeto.", "erro")
            return render_template(
                "painel_tech/projeto_form.html",
                projeto={**projeto, **dados},
                membros=db.listar_membros(),
                capacidades_por_membro=capacidades_por_membro,
                modo="editar",
            )
        db.atualizar_projeto(projeto_id, dados)
        view_utils.registrar_evento(projeto_id, "projeto_editado", "Dados do projeto atualizados")
        flash("Projeto atualizado.", "ok")
        return redirect(url_for("painel_tech.projeto_detalhe", projeto_id=projeto_id))
    return render_template(
        "painel_tech/projeto_form.html",
        projeto=projeto,
        membros=db.listar_membros(),
        capacidades_por_membro=capacidades_por_membro,
        modo="editar",
    )


@bp.route("/projetos/<int:projeto_id>/status", methods=["POST"])
def projeto_status(projeto_id):
    projeto = db.obter_projeto(projeto_id)
    if not projeto:
        abort(404)
    novo_status = request.form.get("status")
    if novo_status not in STATUS:
        abort(400)
    _aplicar_status(projeto_id, novo_status)
    if view_utils.quer_fragmento():
        view_utils.enfileirar_toast("Status atualizado.")
    else:
        flash("Status atualizado.", "ok")
    return view_utils.resposta_projeto(projeto_id)


@bp.route("/projetos/<int:projeto_id>/campo", methods=["POST"])
def projeto_campo(projeto_id):
    """Edição pontual da tabela, sem substituir os demais dados do projeto."""
    projeto = db.obter_projeto(projeto_id)
    if not projeto:
        abort(404)

    campo = (request.form.get("campo") or "").strip()
    valor = (request.form.get("valor") or "").strip()

    if campo == "status":
        if valor not in STATUS:
            return jsonify({"ok": False, "erro": "Status inválido."}), 400
        if projeto.get("status") != valor:
            _aplicar_status(projeto_id, valor)
        return jsonify({"ok": True, "mensagem": "Status atualizado."})

    if campo in INDICADORES:
        if valor not in INDICADORES[campo]["opcoes"]:
            return jsonify({"ok": False, "erro": "Valor inválido."}), 400
        db.atualizar_projeto(projeto_id, {campo: valor})
        view_utils.registrar_evento(
            projeto_id,
            "projeto_editado",
            f"{INDICADORES[campo]['label']} atualizado na tabela",
        )
        return jsonify({"ok": True, "mensagem": f"{INDICADORES[campo]['label']} atualizado."})

    if campo == "responsavel_id":
        responsavel_id = None
        if valor:
            if not valor.isdigit() or not any(
                membro["id"] == int(valor) for membro in db.listar_membros()
            ):
                return jsonify({"ok": False, "erro": "Responsável inválido."}), 400
            responsavel_id = int(valor)
        db.atualizar_projeto(projeto_id, {campo: responsavel_id})
        view_utils.registrar_evento(
            projeto_id, "projeto_editado", "Responsável atualizado na tabela"
        )
        return jsonify({"ok": True, "mensagem": "Responsável atualizado."})

    if campo == "data_prevista_fim":
        if valor:
            try:
                date.fromisoformat(valor)
            except ValueError:
                return jsonify({"ok": False, "erro": "Prazo inválido."}), 400
        db.atualizar_projeto(projeto_id, {campo: valor or None})
        view_utils.registrar_evento(
            projeto_id, "projeto_editado", "Prazo atualizado na tabela"
        )
        return jsonify({"ok": True, "mensagem": "Prazo atualizado."})

    return jsonify({"ok": False, "erro": "Campo não editável pela tabela."}), 400


@bp.route("/projetos/<int:projeto_id>/tempo/play", methods=["POST"])
def projeto_tempo_play(projeto_id):
    if not db.obter_projeto(projeto_id):
        abort(404)
    iniciou = db.iniciar_sessao(projeto_id)
    if iniciou:
        view_utils.registrar_evento(projeto_id, "tempo", "Timer iniciado")
        mensagem, tipo = "Tempo iniciado. ▶", "ok"
    else:
        mensagem, tipo = "O tempo deste projeto já está em andamento.", "erro"
    if view_utils.quer_fragmento():
        view_utils.enfileirar_toast(mensagem, tipo)
    else:
        flash(mensagem, tipo)
    return view_utils.resposta_projeto(projeto_id)


@bp.route("/projetos/<int:projeto_id>/tempo/pause", methods=["POST"])
def projeto_tempo_pause(projeto_id):
    if not db.obter_projeto(projeto_id):
        abort(404)
    segundos = db.pausar_sessao(projeto_id)
    view_utils.registrar_evento(projeto_id, "tempo", "Timer pausado")
    if segundos:
        mensagem, tipo = f"Tempo registrado: {tempo_br(segundos)}.", "ok"
    else:
        mensagem, tipo = "Nenhum tempo em andamento.", "erro"
    if view_utils.quer_fragmento():
        view_utils.enfileirar_toast(mensagem, tipo)
    else:
        flash(mensagem, tipo)
    return view_utils.resposta_projeto(projeto_id)


@bp.route("/projetos/<int:projeto_id>/mover", methods=["POST"])
def projeto_mover(projeto_id):
    projeto = db.obter_projeto(projeto_id)
    if not projeto:
        abort(404)
    novo_status = request.form.get("status")
    if novo_status not in STATUS:
        abort(400)
    coluna_id = (request.form.get("coluna_id") or "").strip()
    coluna = None
    if coluna_id:
        try:
            coluna = kanban_layout.obter_coluna(coluna_id)
        except kanban_layout.ErroLayoutKanban:
            abort(400)
        if coluna["status_base"] != novo_status:
            abort(400)

    if coluna is None or projeto["status"] != novo_status:
        _aplicar_status(projeto_id, novo_status)
    if coluna is not None:
        kanban_layout.atribuir_projeto(projeto_id, coluna_id, novo_status)

    destino = coluna["nome"] if coluna is not None else STATUS[novo_status]["label"]
    if view_utils.quer_fragmento():
        view_utils.enfileirar_toast(f"Projeto movido para {destino}.")
        resposta = render_template(
            "painel_tech/partials/_kanban.html", **_contexto_kanban()
        )
        return view_utils.anexar_toasts(resposta)
    return redirect(url_for("painel_tech.projetos_listar", aba="kanban"))


@bp.route("/projetos/fila/ordem", methods=["POST"])
def fila_ordem():
    ids = [
        int(parte)
        for parte in (request.form.get("ids") or "").split(",")
        if parte.strip().isdigit()
    ]
    if not ids:
        abort(400)
    db.atualizar_ordem_fila(ids)
    if view_utils.quer_fragmento():
        view_utils.enfileirar_toast("Ordem da fila atualizada.")
        resposta = render_template(
            "painel_tech/partials/_kanban.html", **_contexto_kanban()
        )
        return view_utils.anexar_toasts(resposta)
    return redirect(url_for("painel_tech.projetos_listar", aba="kanban"))


@bp.route("/projetos/<int:projeto_id>/excluir", methods=["POST"])
def projeto_excluir(projeto_id):
    projeto = db.obter_projeto(projeto_id)
    if not projeto:
        abort(404)
    db.excluir_projeto(projeto_id)
    flash("Projeto excluído.", "ok")
    return redirect(url_for("painel_tech.projetos_listar"))


@bp.route("/projetos/<int:projeto_id>/comentarios", methods=["POST"])
def projeto_comentar(projeto_id):
    projeto = db.obter_projeto(projeto_id)
    if not projeto:
        abort(404)
    texto = (request.form.get("texto") or "").strip()
    if not texto:
        flash("Escreva um comentário.", "erro")
        return redirect(
            url_for("painel_tech.projeto_detalhe", projeto_id=projeto_id)
        )
    autor = view_utils.usuario_atual()
    db.criar_comentario(projeto_id=projeto_id, autor_nome=autor.get("nome"), texto=texto)
    view_utils.registrar_evento(projeto_id, "comentario", "Comentário adicionado no projeto")
    flash("Comentário adicionado.", "ok")
    return redirect(url_for("painel_tech.projeto_detalhe", projeto_id=projeto_id))
