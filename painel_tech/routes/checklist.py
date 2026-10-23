from datetime import date, datetime, timezone

from flask import abort, flash, redirect, request, url_for

from .. import bp, db, view_utils
from ..domain import label_etapa_status
from ..task_hierarchy import (
    arrange_stages,
    merge_observation,
    reorder_stage_ids,
    split_observation,
    validate_parent,
)


def _dados_etapa(form, parent_id=None):
    return {
        "nome": form.get("nome", "").strip(),
        "responsavel_id": form.get("responsavel_id") or None,
        "status": form.get("status", "pendente"),
        "data_prevista": form.get("data_prevista") or None,
        "observacao": merge_observation(
            form.get("observacao", "").strip(), parent_id
        ),
        "bloqueada": form.get("bloqueada") == "on",
        "bloqueio_motivo": form.get("bloqueio_motivo") or None,
        "bloqueio_descricao": form.get("bloqueio_descricao") or None,
        "bloqueio_desde": form.get("bloqueio_desde") or None,
        "bloqueio_responsavel_id": form.get("bloqueio_responsavel_id") or None,
        "dependencia_id": form.get("dependencia_id") or None,
    }


def _flash(mensagem, categoria="ok"):
    if view_utils.quer_fragmento():
        view_utils.enfileirar_toast(mensagem, categoria)
    else:
        flash(mensagem, categoria)


@bp.route("/projetos/<int:projeto_id>/etapas", methods=["POST"])
def etapa_criar(projeto_id):
    projeto = db.obter_projeto(projeto_id)
    if not projeto:
        abort(404)
    nome = request.form.get("nome", "").strip()
    if not nome:
        _flash("Informe o nome da etapa.", "erro")
        return view_utils.resposta_projeto(projeto_id)
    try:
        parent_id = validate_parent(
            db.listar_etapas(projeto_id), request.form.get("parent_id")
        )
    except ValueError as exc:
        _flash(str(exc), "erro")
        return view_utils.resposta_projeto(projeto_id)
    dados = _dados_etapa(request.form, parent_id)
    dados["nome"] = nome
    dados["ordem"] = db.proxima_ordem_etapa(projeto_id)
    db.criar_etapa(projeto_id, dados)
    db.tocar_projeto(projeto_id)
    view_utils.registrar_evento(projeto_id, "etapa_criada", f"Etapa '{nome}' adicionada")
    _flash("Etapa adicionada.")
    return view_utils.resposta_projeto(projeto_id)


@bp.route("/etapas/<int:etapa_id>/editar", methods=["POST"])
def etapa_editar(etapa_id):
    etapa = db.obter_etapa(etapa_id)
    if not etapa:
        abort(404)
    try:
        parent_id = validate_parent(
            db.listar_etapas(etapa["projeto_id"]),
            request.form.get("parent_id"),
            stage_id=etapa_id,
        )
    except ValueError as exc:
        _flash(str(exc), "erro")
        return view_utils.resposta_projeto(etapa["projeto_id"])
    dados = _dados_etapa(request.form, parent_id)
    if not dados["nome"]:
        _flash("Informe o nome da etapa.", "erro")
        return view_utils.resposta_projeto(etapa["projeto_id"])
    if dados["bloqueada"] and not etapa["bloqueada"]:
        dados["bloqueio_desde"] = dados["bloqueio_desde"] or date.today().isoformat()
    if dados["status"] == "concluida" and etapa["status"] != "concluida":
        dados["data_conclusao"] = date.today().isoformat()
        dados["concluida_em"] = datetime.now(timezone.utc)
    elif dados["status"] != "concluida" and etapa["status"] == "concluida":
        dados["data_conclusao"] = None
        dados["concluida_em"] = None
    db.atualizar_etapa(etapa_id, dados)
    db.tocar_projeto(etapa["projeto_id"])
    view_utils.registrar_evento(etapa["projeto_id"], "etapa_editada", f"Etapa '{dados['nome']}' atualizada", etapa_id)
    _flash("Etapa atualizada.")
    return view_utils.resposta_projeto(etapa["projeto_id"])


@bp.route("/etapas/<int:etapa_id>/concluir", methods=["POST"])
def etapa_concluir(etapa_id):
    etapa = db.obter_etapa(etapa_id)
    if not etapa:
        abort(404)
    if etapa["status"] == "concluida":
        db.atualizar_etapa(
            etapa_id,
            {"status": "pendente", "data_conclusao": None, "concluida_em": None},
        )
        mensagem = "Etapa reaberta"
    else:
        db.atualizar_etapa(
            etapa_id,
            {
                "status": "concluida",
                "data_conclusao": date.today().isoformat(),
                "concluida_em": datetime.now(timezone.utc),
            },
        )
        mensagem = "Etapa concluída"
    db.tocar_projeto(etapa["projeto_id"])
    view_utils.registrar_evento(
        etapa["projeto_id"], "etapa_status", f"{mensagem}: {etapa['nome']}", etapa_id
    )
    return view_utils.resposta_projeto(etapa["projeto_id"])


@bp.route("/etapas/<int:etapa_id>/status", methods=["POST"])
def etapa_status(etapa_id):
    etapa = db.obter_etapa(etapa_id)
    if not etapa:
        abort(404)
    status = request.form.get("status", "pendente")
    if status == etapa["status"]:
        return view_utils.resposta_projeto(etapa["projeto_id"])
    dados = {"status": status}
    if status == "concluida":
        dados["data_conclusao"] = date.today().isoformat()
        dados["concluida_em"] = datetime.now(timezone.utc)
    else:
        dados["data_conclusao"] = None
        dados["concluida_em"] = None
    db.atualizar_etapa(etapa_id, dados)
    db.tocar_projeto(etapa["projeto_id"])
    view_utils.registrar_evento(
        etapa["projeto_id"],
        "etapa_status",
        f"{label_etapa_status(status)['label']}: {etapa['nome']}",
        etapa_id,
    )
    return view_utils.resposta_projeto(etapa["projeto_id"])


@bp.route("/etapas/<int:etapa_id>/bloquear", methods=["POST"])
def etapa_bloquear(etapa_id):
    etapa = db.obter_etapa(etapa_id)
    if not etapa:
        abort(404)
    db.atualizar_etapa(
        etapa_id,
        {
            "bloqueada": True,
            "bloqueio_motivo": request.form.get("bloqueio_motivo") or None,
            "bloqueio_descricao": request.form.get("bloqueio_descricao") or None,
            "bloqueio_desde": request.form.get("bloqueio_desde")
            or date.today().isoformat(),
            "bloqueio_responsavel_id": request.form.get("bloqueio_responsavel_id")
            or None,
        },
    )
    db.tocar_projeto(etapa["projeto_id"])
    view_utils.registrar_evento(
        etapa["projeto_id"], "etapa_bloqueada", f"Etapa bloqueada: {etapa['nome']}", etapa_id
    )
    _flash("Etapa bloqueada.")
    return view_utils.resposta_projeto(etapa["projeto_id"])


@bp.route("/etapas/<int:etapa_id>/desbloquear", methods=["POST"])
def etapa_desbloquear(etapa_id):
    etapa = db.obter_etapa(etapa_id)
    if not etapa:
        abort(404)
    db.atualizar_etapa(
        etapa_id,
        {
            "bloqueada": False,
            "bloqueio_motivo": None,
            "bloqueio_descricao": None,
            "bloqueio_desde": None,
            "bloqueio_responsavel_id": None,
        },
    )
    db.tocar_projeto(etapa["projeto_id"])
    view_utils.registrar_evento(
        etapa["projeto_id"], "etapa_desbloqueada", f"Etapa desbloqueada: {etapa['nome']}", etapa_id
    )
    _flash("Etapa desbloqueada.")
    return view_utils.resposta_projeto(etapa["projeto_id"])


@bp.route("/etapas/<int:etapa_id>/mover", methods=["POST"])
def etapa_mover(etapa_id):
    etapa = db.obter_etapa(etapa_id)
    if not etapa:
        abort(404)
    direcao = request.form.get("direcao", "cima")
    etapas = db.listar_etapas(etapa["projeto_id"])
    hierarquia_ativa = any(
        item.get("_parent_id") for item in arrange_stages(etapas)
    )
    if hierarquia_ativa:
        ordem_atual = [item["id"] for item in etapas]
        ordem_desejada = reorder_stage_ids(etapas, etapa_id, direcao)
        for indice_desejado, item_id in enumerate(ordem_desejada):
            indice_atual = ordem_atual.index(item_id)
            while indice_atual > indice_desejado:
                db.mover_etapa(item_id, "cima")
                ordem_atual[indice_atual - 1], ordem_atual[indice_atual] = (
                    ordem_atual[indice_atual],
                    ordem_atual[indice_atual - 1],
                )
                indice_atual -= 1
    else:
        db.mover_etapa(etapa_id, direcao)
    db.tocar_projeto(etapa["projeto_id"])
    return view_utils.resposta_projeto(etapa["projeto_id"])


@bp.route("/etapas/<int:etapa_id>/excluir", methods=["POST"])
def etapa_excluir(etapa_id):
    etapa = db.obter_etapa(etapa_id)
    if not etapa:
        abort(404)
    projeto_id = etapa["projeto_id"]
    filhas = []
    for relacionada in db.listar_etapas(projeto_id):
        parent_id, observacao_visivel = split_observation(relacionada.get("observacao"))
        if relacionada.get("id") != etapa_id and parent_id == etapa_id:
            filhas.append((relacionada["id"], observacao_visivel))
    db.excluir_etapa(etapa_id)
    for filha_id, observacao_visivel in filhas:
        db.atualizar_etapa(filha_id, {"observacao": observacao_visivel})
    db.tocar_projeto(projeto_id)
    view_utils.registrar_evento(projeto_id, "etapa_excluida", f"Etapa removida: {etapa['nome']}")
    _flash("Etapa removida.")
    return view_utils.resposta_projeto(projeto_id)


@bp.route("/etapas/<int:etapa_id>/comentarios", methods=["POST"])
def etapa_comentar(etapa_id):
    etapa = db.obter_etapa(etapa_id)
    if not etapa:
        abort(404)
    texto = (request.form.get("texto") or "").strip()
    if not texto:
        _flash("Escreva um comentário.", "erro")
        return redirect(
            url_for("painel_tech.projeto_detalhe", projeto_id=etapa["projeto_id"])
        )
    autor = view_utils.usuario_atual()
    db.criar_comentario(
        projeto_id=etapa["projeto_id"],
        etapa_id=etapa_id,
        autor_nome=autor.get("nome"),
        texto=texto,
    )
    view_utils.registrar_evento(
        etapa["projeto_id"],
        "comentario",
        f"Comentário na etapa: {etapa['nome']}",
        etapa_id,
    )
    db.tocar_projeto(etapa["projeto_id"])
    _flash("Comentário adicionado.")
    return redirect(
        url_for("painel_tech.projeto_detalhe", projeto_id=etapa["projeto_id"])
    )
