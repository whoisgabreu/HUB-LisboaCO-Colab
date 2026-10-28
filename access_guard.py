"""Guard central de acesso por tela.

Mapeia prefixos de URL para o código da tela e exige:
- GET/HEAD/OPTIONS -> nível 'ver'
- POST/PUT/PATCH/DELETE -> nível 'editar'

Telas não mapeadas (feed, perfil, agenda, auth, chat, APIs internas) não são
bloqueadas aqui. O guard do Painel TECH continua próprio (em /tech).
"""
from flask import jsonify, redirect, request, session, url_for

import permissions

_MAPA = [
    ("/api/admin/capacidades", "acessos"),
    ("/api/admin/cargos", "acessos"),
    ("/api/admin/posicoes", "acessos"),
    ("/api/admin/telas", "acessos"),
    ("/api/admin/acessos-cargo", "acessos"),
    ("/api/admin/acessos-posicao", "acessos"),
    ("/capacidades", "acessos"),
    ("/acessos", "acessos"),
    ("/api/admin/usuarios", "usuarios"),
    ("/gerenciar-usuarios", "usuarios"),
    ("/api/admin/squads", "squads"),
    ("/api/squads", "squads"),
    ("/squads", "squads"),
    ("/api/feed/config", "feed_config"),
    ("/feed-config", "feed_config"),
    ("/admin/mrr-historico", "mrr_historico"),
    ("/api/mrr", "mrr_historico"),
    ("/hub-remuneracao", "remuneracao"),
    ("/api/remuneracao", "remuneracao"),
    ("/automacoes", "automacoes"),
    ("/api/automacoes", "automacoes"),
    ("/hub-metricas", "metricas"),
    ("/painel-ranking", "ranking"),
    ("/api/ranking", "ranking"),
    ("/hub-projetos", "projetos"),
    ("/api/projetos", "projetos"),
    ("/api/admin/investidores-ativos", "projetos"),
    ("/kanban", "kanban"),
    ("/api/kanban", "kanban"),
    ("/operacao", "operacao"),
    ("/api/operacao", "operacao"),
    ("/criativa", "criativa"),
    ("/api/criativa", "criativa"),
    ("/grupos", "grupos"),
    ("/hub-cs-cx", "cs_cx"),
    ("/padrao-nomenclaturas", "nomenclaturas"),
    ("/prompts-gt-ia", "prompts"),
    ("/api/desabafo", "desabafo"),
    ("/desabafo", "desabafo"),
]
_MAPA.sort(key=lambda par: len(par[0]), reverse=True)

# Rotas de escrita liberadas com nível 'ver' (ex.: qualquer logado pode postar no Desabafo)
_POST_COM_VER = {"/api/desabafo"}


def tela_do_path(path: str):
    for prefixo, tela in _MAPA:
        if path == prefixo or path.startswith(prefixo + "/"):
            return tela
    return None


def _escrita_projeto_responsavel(path: str) -> bool:
    """Escritas do modal do projeto que o responsável pode executar mesmo com 'ver'."""
    partes = path.strip("/").split("/")
    if len(partes) < 3 or partes[:2] != ["api", "projetos"]:
        return False
    if not partes[2].isdigit():
        return False
    if len(partes) == 3:
        return True
    return partes[3] in ("contexto", "contexto-geral", "contas")


def init_app(app):
    @app.before_request
    def _acesso_por_tela():
        if not session.get("nome"):
            return None
        if request.path.startswith("/static") or request.path == "/tech" or request.path.startswith("/tech/"):
            return None
        tela = tela_do_path(request.path)
        if not tela:
            return None
        nivel = "ver" if request.method in ("GET", "HEAD", "OPTIONS") else "editar"
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if request.path in _POST_COM_VER:
                nivel = "ver"
            elif _escrita_projeto_responsavel(request.path):
                # Autorização fina é feita no endpoint (responsável pelo projeto
                # pode não ter 'editar' na tela de projetos).
                nivel = "ver"
        if permissions.pode_tela(tela, nivel):
            return None
        if request.path.startswith("/api/"):
            return jsonify({"error": "Sem permissão para esta tela."}), 403
        return redirect(url_for("feed"))

    return app