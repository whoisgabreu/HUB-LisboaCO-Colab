import json

from flask import jsonify, request

from .. import bp, kanban_layout


@bp.route("/projetos/kanban/layout", methods=["POST"])
def kanban_layout_salvar():
    payload = request.get_json(silent=True)
    if payload is None:
        bruto = request.form.get("colunas", "")
        try:
            payload = {"colunas": json.loads(bruto)}
        except (TypeError, json.JSONDecodeError):
            return jsonify({"ok": False, "erro": "Configuração de colunas inválida."}), 400

    if not isinstance(payload, dict):
        return jsonify({"ok": False, "erro": "Configuração de colunas inválida."}), 400

    try:
        estado = kanban_layout.salvar_colunas(payload.get("colunas"))
    except kanban_layout.ErroLayoutKanban as erro:
        return jsonify({"ok": False, "erro": str(erro)}), 400

    return jsonify(
        {
            "ok": True,
            "mensagem": "Colunas do Kanban atualizadas.",
            "colunas": estado["colunas"],
        }
    )
