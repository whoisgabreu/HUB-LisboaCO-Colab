import hmac
import os
import secrets

from flask import session


def csrf_ativo(app):
    if app.config.get("TESTING"):
        return False
    return os.getenv("CSRF_ATIVO", "1").lower() in ("1", "true", "sim", "yes")


def novo_token(app):
    if not csrf_ativo(app):
        return ""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def validar(token, app):
    if not csrf_ativo(app):
        return True
    esperado = session.get("csrf_token")
    if not esperado or not token:
        return False
    return hmac.compare_digest(esperado, token)