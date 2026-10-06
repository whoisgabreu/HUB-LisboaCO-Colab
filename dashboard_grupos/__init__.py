import os

from flask import Blueprint

bp = Blueprint(
    "dashboard_grupos",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static/dashboard_grupos",
    url_prefix="/grupos",
)

from . import routes  # noqa: E402


def create_app():
    from flask import Flask

    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-dashboard-grupos")
    app.register_blueprint(bp)
    return app