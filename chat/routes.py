"""Endpoints JSON do Chat interno do HUB."""

from flask import jsonify, request, session

from database import Session
from chat.service import ChatService

from . import bp


def _erro(e: Exception):
    if isinstance(e, PermissionError):
        return jsonify({"erro": str(e)}), 403
    if isinstance(e, ValueError):
        return jsonify({"erro": str(e)}), 400
    import traceback

    traceback.print_exc()
    return jsonify({"erro": "Erro interno ao processar a requisição."}), 500


def _email() -> str:
    return session.get("email", "")


# ── Conversas ─────────────────────────────────────────────────────────────────


@bp.route("/conversas", methods=["GET"])
def listar_conversas():
    with Session() as db:
        try:
            return jsonify({"conversas": ChatService(db).listar_conversas(_email())})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/conversas", methods=["POST"])
def criar_conversa():
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            return jsonify(ChatService(db).obter_ou_criar_conversa(_email(), payload.get("email")))
        except Exception as e:  # noqa: BLE001
            return _erro(e)


# ── Usuários / busca ──────────────────────────────────────────────────────────


@bp.route("/usuarios", methods=["GET"])
def listar_usuarios():
    with Session() as db:
        try:
            return jsonify({"usuarios": ChatService(db).listar_usuarios_ativos(_email())})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/busca", methods=["GET"])
def buscar():
    with Session() as db:
        try:
            return jsonify(ChatService(db).buscar(_email(), request.args.get("q", "")))
        except Exception as e:  # noqa: BLE001
            return _erro(e)


# ── Mensagens ─────────────────────────────────────────────────────────────────


@bp.route("/conversas/<int:conversa_id>/mensagens", methods=["GET"])
def listar_mensagens(conversa_id):
    cursor = request.args.get("cursor", type=int)
    with Session() as db:
        try:
            return jsonify(
                ChatService(db).listar_mensagens(conversa_id, _email(), cursor=cursor)
            )
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/conversas/<int:conversa_id>/mensagens", methods=["POST"])
def enviar_mensagem(conversa_id):
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            return jsonify(
                ChatService(db).enviar_mensagem(conversa_id, _email(), payload.get("conteudo"))
            ), 201
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/mensagens/<int:mensagem_id>/editar", methods=["POST", "PUT"])
def editar_mensagem(mensagem_id):
    payload = request.get_json(silent=True) or {}
    with Session() as db:
        try:
            return jsonify(ChatService(db).editar_mensagem(mensagem_id, _email(), payload.get("conteudo")))
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/mensagens/<int:mensagem_id>", methods=["DELETE"])
def deletar_mensagem(mensagem_id):
    with Session() as db:
        try:
            ChatService(db).deletar_mensagem(mensagem_id, _email())
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/conversas/<int:conversa_id>/ler", methods=["POST"])
def marcar_lida(conversa_id):
    with Session() as db:
        try:
            ChatService(db).marcar_lida(conversa_id, _email())
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


# ── Não lidas / presença ──────────────────────────────────────────────────────


@bp.route("/nao-lidas", methods=["GET"])
def nao_lidas():
    with Session() as db:
        try:
            return jsonify({"total": ChatService(db).total_nao_lidas(_email())})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/marcar-todas-lidas", methods=["POST"])
def marcar_todas_lidas():
    with Session() as db:
        try:
            ChatService(db).marcar_todas_lidas(_email())
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)


@bp.route("/presenca/ping", methods=["POST"])
def ping():
    with Session() as db:
        try:
            ChatService(db).ping(_email())
            return jsonify({"ok": True})
        except Exception as e:  # noqa: BLE001
            return _erro(e)
