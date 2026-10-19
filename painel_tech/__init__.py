import os

from dotenv import load_dotenv
from flask import Blueprint, Flask

load_dotenv()

bp = Blueprint(
    "painel_tech",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static/painel_tech",
)


def create_app():
    from flask import abort, render_template, request

    from . import security, ui

    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "painel-tech-dev")
    app.register_blueprint(bp)
    ui.registrar(app)
    app.jinja_env.globals["csrf_token"] = lambda: security.novo_token(app)

    @app.before_request
    def verificar_csrf():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            token = request.headers.get("X-CSRF-Token") or request.form.get(
                "csrf_token"
            )
            if not security.validar(token, app):
                abort(400)

    @app.errorhandler(400)
    def erro_400(_erro):
        return (
            render_template("painel_tech/erro.html", codigo=400, mensagem="Requisição inválida"),
            400,
        )

    @app.errorhandler(404)
    def erro_404(_erro):
        return (
            render_template(
                "painel_tech/erro.html", codigo=404, mensagem="Página não encontrada"
            ),
            404,
        )

    @app.errorhandler(500)
    def erro_500(_erro):
        return (
            render_template("painel_tech/erro.html", codigo=500, mensagem="Erro interno do servidor"),
            500,
        )

    return app


from . import routes  # noqa: E402,F401
