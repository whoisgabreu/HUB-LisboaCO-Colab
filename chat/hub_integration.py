"""Integração do Chat interno ao HUB Lisboa&CO.

Módulo isolado que registra o blueprint ``chat`` e aplica o guard de sessão.
Não altera database.py, models.py ou services do HUB além do registro no app.
"""

from . import bp


def register(app):
    """Registra o blueprint do chat no app do HUB."""
    from flask import jsonify, session

    @bp.before_request
    def _guard_sessao():
        if "nome" not in session:
            return jsonify({"erro": "Sessão expirada. Faça login novamente."}), 401

    app.register_blueprint(bp)
    return bp
