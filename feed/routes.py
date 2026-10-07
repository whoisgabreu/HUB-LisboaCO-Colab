"""Endpoints JSON do Feed social do HUB."""

from datetime import datetime

from flask import jsonify, request, session

from database import Session
from feed.service import FeedService, is_gestao_feed, is_privilegiado

from . import bp


def _erro(e: Exception):
    if isinstance(e, PermissionError):
        return jsonify({"erro": str(e)}), 403
    if isinstance(e, ValueError):
        return jsonify({"erro": str(e)}), 400
    import traceback

    traceback.print_exc()
    return jsonify({"erro": "Erro interno ao processar a requisição."}), 500


def _privilegiado() -> bool:
    return is_privilegiado(session.get("posicao", ""), session.get("nivel_acesso", ""))


def _gestao() -> bool:
    return is_gestao_feed(session.get("posicao", ""), session.get("nivel_acesso", ""))


def _email() -> str:
    return session.get("email", "")


def _viewer() -> dict:
    return {
        "posicao": session.get("posicao", ""),
        "nivel_acesso": session.get("nivel_acesso", ""),
        "squad": session.get("squad", ""),
    }


def _parse_evento_data(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", ""))
    except ValueError:
        raise ValueError("Data do evento inválida.")


# ── Posts ─────────────────────────────────────────────────────────────────────


@bp.route("/posts", methods=["GET"])
def listar_posts():
    v = _viewer()
    with Session() as db:
        try:
            return jsonify(
                FeedService(db).listar_posts(
                    _email(),
                    cursor=request.args.get("cursor"),
                    por_pagina=request.args.get("por_pagina", 10, type=int),
                    q=request.args.get("q"),
                    tipo=request.args.get("tipo"),
                    autor=request.args.get("autor"),
                    salvos=request.args.get("salvos", "").lower() in ("1", "true", "sim"),
                    posicao=v["posicao"],
                    nivel_acesso=v["nivel_acesso"],
                    squad=v["squad"],
                )
            )
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/novos", methods=["GET"])
def novos_posts():
    v = _viewer()
    with Session() as db:
        try:
            return jsonify(
                FeedService(db).novos_posts(
                    request.args.get("desde", ""),
                    _email(),
                    posicao=v["posicao"],
                    nivel_acesso=v["nivel_acesso"],
                    squad=v["squad"],
                )
            )
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/posts", methods=["POST"])
def criar_post():
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            post = FeedService(db).criar_post(
                _email(), payload.get("conteudo"), payload.get("visibilidade", "todos")
            )
            return jsonify(post), 201
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/eventos", methods=["POST"])
def criar_evento():
    if not _privilegiado():
        return jsonify({"erro": "Sem permissão para criar eventos."}), 403
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            evento = FeedService(db).criar_evento(
                _email(),
                payload.get("titulo"),
                payload.get("conteudo"),
                _parse_evento_data(payload.get("evento_data")),
                payload.get("evento_local"),
                payload.get("dias_fixado", 1),
                payload.get("visibilidade", "todos"),
            )
            return jsonify(evento), 201
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/enquetes", methods=["POST"])
def criar_enquete():
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            enquete = FeedService(db).criar_enquete(
                _email(),
                payload.get("pergunta"),
                payload.get("opcoes", []),
                payload.get("visibilidade", "todos"),
            )
            return jsonify(enquete), 201
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/posts/<int:post_id>/repostar", methods=["POST"])
def repostar(post_id):
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            post = FeedService(db).repostar(
                post_id, _email(), payload.get("comentario"), payload.get("visibilidade", "todos")
            )
            return jsonify(post), 201
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/posts/<int:post_id>/editar", methods=["POST", "PUT"])
def editar_post(post_id):
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            post = FeedService(db).editar_post(post_id, _email(), payload.get("conteudo"))
            return jsonify(post)
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/posts/<int:post_id>", methods=["DELETE"])
def deletar_post(post_id):
    with Session() as db:
        try:
            FeedService(db).deletar_post(post_id, _email(), _gestao())
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


# ── Reações ───────────────────────────────────────────────────────────────────


@bp.route("/posts/<int:post_id>/reagir", methods=["POST"])
def reagir(post_id):
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            return jsonify(FeedService(db).reagir(post_id, _email(), payload.get("tipo")))
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/comentarios/<int:comentario_id>/reagir", methods=["POST"])
def reagir_comentario(comentario_id):
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            return jsonify(
                FeedService(db).reagir_comentario(comentario_id, _email(), payload.get("tipo"))
            )
        except Exception as e:  # noqa: BLE001
            return _erro(e)


# ── Enquetes / salvos ─────────────────────────────────────────────────────────


@bp.route("/posts/<int:post_id>/votar", methods=["POST"])
def votar(post_id):
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            return jsonify(
                FeedService(db).votar_enquete(post_id, _email(), payload.get("opcao_index"))
            )
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/posts/<int:post_id>/salvar", methods=["POST"])
def salvar(post_id):
    with Session() as db:
        try:
            return jsonify(FeedService(db).alternar_salvo(post_id, _email()))
        except Exception as e:  # noqa: BLE001
            return _erro(e)


# ── Comentários ───────────────────────────────────────────────────────────────


@bp.route("/posts/<int:post_id>/comentarios", methods=["GET"])
def listar_comentarios(post_id):
    with Session() as db:
        try:
            return jsonify(
                {"comentarios": FeedService(db).listar_comentarios(post_id, _email())}
            )
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/posts/<int:post_id>/comentarios", methods=["POST"])
def comentar(post_id):
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            comentario = FeedService(db).comentar(
                post_id, _email(), payload.get("conteudo"), payload.get("parent_id")
            )
            return jsonify(comentario), 201
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/comentarios/<int:comentario_id>", methods=["DELETE"])
def deletar_comentario(comentario_id):
    with Session() as db:
        try:
            FeedService(db).deletar_comentario(comentario_id, _email(), _gestao())
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


# ── Fixação / moderação ───────────────────────────────────────────────────────


@bp.route("/posts/<int:post_id>/fixar", methods=["POST"])
def fixar_post(post_id):
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            FeedService(db).fixar_post(
                post_id, _email(), _gestao(), payload.get("dias", 7)
            )
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/posts/<int:post_id>/desfixar", methods=["POST"])
def desfixar_post(post_id):
    with Session() as db:
        try:
            FeedService(db).desfixar_post(post_id, _email(), _gestao())
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/posts/<int:post_id>/ocultar", methods=["POST"])
def ocultar_post(post_id):
    if not _gestao():
        return jsonify({"erro": "Sem permissão para ocultar posts."}), 403
    with Session() as db:
        try:
            FeedService(db).ocultar_post(post_id, True)
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/posts/<int:post_id>/desocultar", methods=["POST"])
def desocultar_post(post_id):
    if not _gestao():
        return jsonify({"erro": "Sem permissão para reexibir posts."}), 403
    with Session() as db:
        try:
            FeedService(db).ocultar_post(post_id, False)
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/posts/<int:post_id>/denunciar", methods=["POST"])
def denunciar_post(post_id):
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            FeedService(db).denunciar_post(post_id, _email(), payload.get("motivo"))
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


# ── Perfil / usuários ─────────────────────────────────────────────────────────


@bp.route("/usuarios", methods=["GET"])
def usuarios():
    with Session() as db:
        try:
            return jsonify({"usuarios": FeedService(db).listar_usuarios_para_mencao()})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/perfil/<path:email>", methods=["GET"])
def perfil(email):
    with Session() as db:
        try:
            return jsonify(FeedService(db).perfil_usuario(email))
        except Exception as e:  # noqa: BLE001
            return _erro(e)


# ── Notificações ──────────────────────────────────────────────────────────────


@bp.route("/notificacoes", methods=["GET"])
def notificacoes():
    with Session() as db:
        try:
            return jsonify({"notificacoes": FeedService(db).listar_notificacoes(_email())})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/notificacoes/contagem", methods=["GET"])
def notificacoes_contagem():
    with Session() as db:
        try:
            return jsonify({"nao_lidas": FeedService(db).contar_nao_lidas(_email())})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/notificacoes/<int:notificacao_id>/lida", methods=["POST"])
def notificacao_lida(notificacao_id):
    with Session() as db:
        try:
            FeedService(db).marcar_lida(notificacao_id, _email())
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/notificacoes/marcar-lidas", methods=["POST"])
def notificacoes_marcar_lidas():
    with Session() as db:
        try:
            FeedService(db).marcar_todas_lidas(_email())
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


# ── Widgets ───────────────────────────────────────────────────────────────────


@bp.route("/widgets", methods=["GET"])
def widgets():
    with Session() as db:
        try:
            svc = FeedService(db)
            return jsonify(
                {
                    "aniversariantes": svc.aniversariantes_do_dia(),
                    "proximos_eventos": svc.proximos_eventos(),
                    "em_alta": svc.em_alta(),
                    "ranking": svc.ranking_participacao(),
                }
            )
        except Exception as e:  # noqa: BLE001
            return _erro(e)
