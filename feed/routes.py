"""Endpoints JSON do Feed social do HUB."""

from datetime import datetime

from flask import jsonify, request, session

from database import Session
from feed.service import FeedService, is_privilegiado

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
    pagina = request.args.get("pagina", 1, type=int)
    with Session() as db:
        try:
            return jsonify(FeedService(db).listar_posts(session.get("email"), pagina))
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/posts", methods=["POST"])
def criar_post():
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            post = FeedService(db).criar_post(session.get("email"), payload.get("conteudo"))
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
                session.get("email"),
                payload.get("titulo"),
                payload.get("conteudo"),
                _parse_evento_data(payload.get("evento_data")),
                payload.get("evento_local"),
                payload.get("dias_fixado", 1),
            )
            return jsonify(evento), 201
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/posts/<int:post_id>", methods=["DELETE"])
def deletar_post(post_id):
    with Session() as db:
        try:
            FeedService(db).deletar_post(post_id, session.get("email"), _privilegiado())
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


# ── Reações ───────────────────────────────────────────────────────────────────


@bp.route("/posts/<int:post_id>/reagir", methods=["POST"])
def reagir(post_id):
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            resultado = FeedService(db).reagir(
                post_id, session.get("email"), payload.get("tipo")
            )
            return jsonify(resultado)
        except Exception as e:  # noqa: BLE001
            return _erro(e)


# ── Comentários ───────────────────────────────────────────────────────────────


@bp.route("/posts/<int:post_id>/comentarios", methods=["GET"])
def listar_comentarios(post_id):
    with Session() as db:
        try:
            return jsonify({"comentarios": FeedService(db).listar_comentarios(post_id)})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/posts/<int:post_id>/comentarios", methods=["POST"])
def comentar(post_id):
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            comentario = FeedService(db).comentar(
                post_id,
                session.get("email"),
                payload.get("conteudo"),
                payload.get("parent_id"),
            )
            return jsonify(comentario), 201
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/comentarios/<int:comentario_id>", methods=["DELETE"])
def deletar_comentario(comentario_id):
    with Session() as db:
        try:
            FeedService(db).deletar_comentario(
                comentario_id, session.get("email"), _privilegiado()
            )
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


# ── Fixação ───────────────────────────────────────────────────────────────────


@bp.route("/posts/<int:post_id>/fixar", methods=["POST"])
def fixar_post(post_id):
    if not _privilegiado():
        return jsonify({"erro": "Sem permissão para fixar posts."}), 403
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            FeedService(db).fixar_post(post_id, payload.get("dias", 7))
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/posts/<int:post_id>/desfixar", methods=["POST"])
def desfixar_post(post_id):
    if not _privilegiado():
        return jsonify({"erro": "Sem permissão para desfixar posts."}), 403
    with Session() as db:
        try:
            FeedService(db).desfixar_post(post_id)
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)
