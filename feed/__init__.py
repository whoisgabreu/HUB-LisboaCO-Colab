"""Blueprint isolado do Feed social do HUB (APIs JSON).

A UI é renderizada na home; este módulo expõe apenas os endpoints
``/api/feed/*``.
"""

from flask import Blueprint

bp = Blueprint("feed", __name__, url_prefix="/api/feed")

from . import routes  # noqa: E402,F401
