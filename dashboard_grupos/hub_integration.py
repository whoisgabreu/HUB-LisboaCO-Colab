"""Integração do dashboard de grupos ao HUB Lisboa&CO.

Módulo isolado que registra o blueprint ``dashboard_grupos`` no app do HUB,
injeta a conexão de banco a partir das variáveis já existentes no HUB e
aplica o controle de acesso (Gerência / Sócio / Coordenador).

Não altera database.py, models ou services do HUB.
"""

import os
import unicodedata
from urllib.parse import quote_plus

_POSICOES_PERMITIDAS = {"Gerência", "Sócio", "Coordenador"}


def _montar_db_url():
    """Deriva a URL externa a partir das variáveis DB_* do HUB."""
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    database = os.getenv("DB_DATABASE")
    user = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")
    if not all([host, port, database, user, password]):
        return None
    user_enc = quote_plus(user)
    pass_enc = quote_plus(password)
    return f"postgresql://{user_enc}:{pass_enc}@{host}:{port}/{database}"


def _injetar_envs():
    """Garante que o db.py do dashboard encontre a conexão e os paths corretos."""
    if not os.getenv("DB_EXTERNAL_URL"):
        url = _montar_db_url()
        if url:
            os.environ["DB_EXTERNAL_URL"] = url

    base = os.path.dirname(__file__)
    raiz = os.path.abspath(os.path.join(base, ".."))
    os.environ.setdefault("EQUIPE_PATH", os.path.join(raiz, "equipe.json"))
    os.environ.setdefault("CLIENTES_PATH", os.path.join(raiz, "clientes.json"))
    os.environ.setdefault("CHURN_PATH", os.path.join(raiz, "churn.json"))


def _posicao_normalizada(valor):
    if not valor:
        return ""
    return unicodedata.normalize("NFC", str(valor).strip().lower())


def _permitido(posicao):
    return _posicao_normalizada(posicao) in {
        _posicao_normalizada(p) for p in _POSICOES_PERMITIDAS
    }


def register(app):
    """Registra o blueprint do dashboard no app do HUB."""
    _injetar_envs()

    from . import bp

    @bp.before_request
    def _guard_acesso():
        from flask import redirect, render_template, session, url_for

        if "nome" not in session:
            return redirect(url_for("login"))
        if not _permitido(session.get("posicao")):
            return render_template("index.html", error="Acesso restrito.")

    app.register_blueprint(bp)
    return bp
