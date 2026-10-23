"""Integração do Painel Gerencial TECH no HUB.

Registra o blueprint do painel sob ``/tech`` usando a sessão/permissões do HUB:
- Todos os usuários logados podem VISUALIZAR.
- Apenas quem tem a capacidade ``tech`` (ou Admin/gestão ampla) pode EDITAR/gerenciar.
"""
from flask import abort, redirect, render_template, request, session, url_for

ESCRITA = ("POST", "PUT", "PATCH", "DELETE")


def _pode_editar() -> bool:
    import permissions

    return (
        permissions.tem(permissions.CAP_TECH)
        or permissions.is_admin()
        or permissions.is_gestao_ampla()
        or permissions.pode_editar_tela("tech")
    )


def _pode_ver() -> bool:
    import permissions

    return _pode_editar() or permissions.pode_tela("tech", "ver")


def register(app):
    """Registra o painel no app do HUB. Idempotente."""
    if "painel_tech" in app.blueprints:
        return app.blueprints["painel_tech"]

    from . import bp, security, ui

    # Hooks do blueprint DEVEM ser definidos antes do register_blueprint.
    @bp.before_request
    def _guard():
        if "nome" not in session:
            return redirect(url_for("login"))
        if request.method not in ESCRITA and not _pode_ver():
            return redirect(url_for("feed"))
        if request.method in ESCRITA:
            if not _pode_editar():
                abort(403)
            token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
            if not security.validar(token, app):
                abort(400)

    @bp.errorhandler(400)
    def _erro_400(_e):
        return render_template("painel_tech/erro.html", codigo=400, mensagem="Requisição inválida"), 400

    @bp.errorhandler(403)
    def _erro_403(_e):
        return render_template(
            "painel_tech/erro.html",
            codigo=403,
            mensagem="Apenas a posição TECH (ou Admin/gestão) pode editar este painel.",
        ), 403

    app.register_blueprint(bp, url_prefix="/tech")

    ui.registrar(app)
    app.jinja_env.globals["csrf_token"] = lambda: security.novo_token(app)

    @app.context_processor
    def _injetar_pode_editar():
        try:
            return {"pode_editar": _pode_editar()}
        except Exception:  # noqa: BLE001
            return {"pode_editar": False}

    return bp
