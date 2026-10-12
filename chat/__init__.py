"""Blueprint isolado do Chat interno do HUB (APIs JSON)."""

from flask import Blueprint

bp = Blueprint("chat", __name__, url_prefix="/api/chat")

from . import routes  # noqa: E402,F401
