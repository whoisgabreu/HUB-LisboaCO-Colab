"""Núcleo de permissões e contexto de usuário do HUB v2.

Lê as tabelas ``v2_`` (cargos, posições, capacidades, squads) e calcula as
capacidades efetivas de um usuário como a **união** das capacidades concedidas
pelas suas posições e pelo seu cargo.

Não toca em tabelas de produção; apenas lê as estruturas ``v2_``.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import text

SCHEMA = "plataforma_geral"

# Todos os códigos de capacidade conhecidos pela aplicação.
CAP_ADMIN = "admin"
CAP_GESTAO_AMPLA = "gestao_ampla"
CAP_GESTAO_SQUAD = "gestao_squad"
CAP_OPERACAO_ACCOUNT = "operacao_account"
CAP_OPERACAO_GT = "operacao_gt"
CAP_CRIATIVA = "criativa"
CAP_CS_CX = "cs_cx"
CAP_TECH = "tech"
CAP_PEOPLE = "people"


# ── Consultas (db) ───────────────────────────────────────────────────────────


def carregar_contexto(db, investidor_id: Optional[int]) -> Dict[str, Any]:
    """Retorna cargo, posições, squads e capacidades efetivas do usuário."""
    vazio = {"cargo": None, "posicoes": [], "squads": [], "capacidades": []}
    if not investidor_id:
        return vazio

    cargo = db.execute(
        text(f"SELECT cargo FROM {SCHEMA}.v2_investidor_cargo WHERE investidor_id = :i"),
        {"i": investidor_id},
    ).scalar()

    posicoes = [
        r[0]
        for r in db.execute(
            text(f"SELECT posicao FROM {SCHEMA}.v2_investidor_posicoes WHERE investidor_id = :i"),
            {"i": investidor_id},
        ).all()
    ]

    squads_rows = db.execute(
        text(
            f"""
            SELECT s.id, s.nome
            FROM {SCHEMA}.v2_investidor_squads isq
            JOIN {SCHEMA}.v2_squads s ON s.id = isq.squad_id
            WHERE isq.investidor_id = :i AND s.ativo = TRUE
            ORDER BY s.ordem, s.nome
            """
        ),
        {"i": investidor_id},
    ).all()
    squads = [{"id": r[0], "nome": r[1]} for r in squads_rows]

    capacidades = set()
    if posicoes:
        for (cap,) in db.execute(
            text(f"SELECT capacidade FROM {SCHEMA}.v2_posicao_capacidades WHERE posicao = ANY(:p)"),
            {"p": posicoes},
        ).all():
            capacidades.add(cap)
    if cargo:
        for (cap,) in db.execute(
            text(f"SELECT capacidade FROM {SCHEMA}.v2_cargo_capacidades WHERE cargo = :c"),
            {"c": cargo},
        ).all():
            capacidades.add(cap)

    return {
        "cargo": cargo,
        "posicoes": posicoes,
        "squads": squads,
        "capacidades": sorted(capacidades),
        "pode_gerenciar_feed": bool(flag_gerenciar_feed(db, investidor_id)),
    }


def flag_gerenciar_feed(db, investidor_id: Optional[int]) -> bool:
    """Flag por usuário: pode criar eventos e fixar posts no feed."""
    if not investidor_id:
        return False
    try:
        valor = db.execute(
            text(f"SELECT pode_gerenciar_feed FROM {SCHEMA}.v2_investidor_flags WHERE investidor_id = :i"),
            {"i": investidor_id},
        ).scalar()
    except Exception:
        return False
    return bool(valor)


def definir_flag_gerenciar_feed(db, investidor_id, valor) -> None:
    if not investidor_id:
        return
    db.execute(
        text(
            f"INSERT INTO {SCHEMA}.v2_investidor_flags (investidor_id, pode_gerenciar_feed) "
            "VALUES (:i, :v) ON CONFLICT (investidor_id) DO UPDATE SET pode_gerenciar_feed = EXCLUDED.pode_gerenciar_feed"
        ),
        {"i": investidor_id, "v": bool(valor)},
    )


def config_get(db, chave: str, default=None):
    """Lê um valor de v2_config (key/value)."""
    try:
        valor = db.execute(
            text(f"SELECT valor FROM {SCHEMA}.v2_config WHERE chave = :c"),
            {"c": chave},
        ).scalar()
    except Exception:
        return default
    return valor if valor not in (None, "") else default


def config_set(db, chave: str, valor) -> None:
    db.execute(
        text(
            f"INSERT INTO {SCHEMA}.v2_config (chave, valor) VALUES (:c, :v) "
            "ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor"
        ),
        {"c": chave, "v": valor},
    )


def cargo_do_investidor(db, investidor_id: Optional[int]) -> Optional[str]:
    if not investidor_id:
        return None
    return db.execute(
        text(f"SELECT cargo FROM {SCHEMA}.v2_investidor_cargo WHERE investidor_id = :i"),
        {"i": investidor_id},
    ).scalar()


def squad_ids_do_investidor(db, investidor_id: Optional[int]) -> List[int]:
    if not investidor_id:
        return []
    return [
        r[0]
        for r in db.execute(
            text(f"SELECT squad_id FROM {SCHEMA}.v2_investidor_squads WHERE investidor_id = :i"),
            {"i": investidor_id},
        ).all()
    ]


def emails_da_squad(db, squad_id: Optional[int]) -> List[str]:
    """E-mails dos investidores vinculados a uma squad (por id)."""
    if not squad_id:
        return []
    rows = db.execute(
        text(
            f"""
            SELECT i.email
            FROM {SCHEMA}.v2_investidor_squads isq
            JOIN {SCHEMA}.investidores i ON i.id = isq.investidor_id
            WHERE isq.squad_id = :s AND i.email IS NOT NULL
            """
        ),
        {"s": squad_id},
    ).all()
    return [r[0] for r in rows if r[0]]


def listar_squads(db, apenas_ativas: bool = True, ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    conds = []
    params: Dict[str, Any] = {}
    if apenas_ativas:
        conds.append("ativo = TRUE")
    if ids:
        conds.append("id = ANY(:ids)")
        params["ids"] = ids
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    rows = db.execute(
        text(f"SELECT id, nome, ativo, ordem FROM {SCHEMA}.v2_squads {where} ORDER BY ordem, nome"),
        params,
    ).all()
    return [{"id": r[0], "nome": r[1], "ativo": r[2], "ordem": r[3]} for r in rows]


def listar_catalogo(db, tabela: str) -> List[Dict[str, Any]]:
    """Lista cargos/posicoes/capacidades ativos (tabela sanitizada)."""
    permitidas = {"v2_cargos": "nome", "v2_posicoes": "nome", "v2_capacidades": "codigo"}
    if tabela not in permitidas:
        raise ValueError("Catálogo inválido.")
    col = permitidas[tabela]
    where = "" if tabela == "v2_capacidades" else "WHERE ativo = TRUE"
    rows = db.execute(
        text(f"SELECT {col}, ordem FROM {SCHEMA}.{tabela} {where} ORDER BY ordem, {col}")
    ).all()
    return [r[0] for r in rows]


# ── Squads / projetos por id (v2_) ───────────────────────────────────────────


def projeto_ids_das_squads(db, squad_ids) -> List[int]:
    ids = squad_ids or []
    if not ids:
        return []
    rows = db.execute(
        text(
            f"SELECT DISTINCT pipefy_id FROM {SCHEMA}.v2_projeto_squads WHERE squad_id = ANY(:s)"
        ),
        {"s": ids},
    ).all()
    return [r[0] for r in rows]


def squads_do_projeto(db, pipefy_id) -> List[Dict[str, Any]]:
    if pipefy_id is None:
        return []
    rows = db.execute(
        text(
            f"""
            SELECT s.id, s.nome
            FROM {SCHEMA}.v2_projeto_squads ps
            JOIN {SCHEMA}.v2_squads s ON s.id = ps.squad_id
            WHERE ps.pipefy_id = :p
            ORDER BY s.ordem, s.nome
            """
        ),
        {"p": pipefy_id},
    ).all()
    return [{"id": r[0], "nome": r[1]} for r in rows]


def definir_squads_do_projeto(db, pipefy_id, squad_ids) -> None:
    db.execute(
        text(f"DELETE FROM {SCHEMA}.v2_projeto_squads WHERE pipefy_id = :p"),
        {"p": pipefy_id},
    )
    for sid in squad_ids or []:
        db.execute(
            text(
                f"INSERT INTO {SCHEMA}.v2_projeto_squads (pipefy_id, squad_id) VALUES (:p, :s) "
                "ON CONFLICT (pipefy_id, squad_id) DO NOTHING"
            ),
            {"p": pipefy_id, "s": sid},
        )


# ── Escrita de vínculos de usuário (v2_) ─────────────────────────────────────


def definir_cargo(db, investidor_id, cargo) -> None:
    if cargo:
        db.execute(
            text(
                f"INSERT INTO {SCHEMA}.v2_investidor_cargo (investidor_id, cargo, atualizado_em) "
                "VALUES (:i, :c, NOW()) ON CONFLICT (investidor_id) DO UPDATE SET cargo = EXCLUDED.cargo, atualizado_em = NOW()"
            ),
            {"i": investidor_id, "c": cargo},
        )
    else:
        db.execute(
            text(f"DELETE FROM {SCHEMA}.v2_investidor_cargo WHERE investidor_id = :i"),
            {"i": investidor_id},
        )


def definir_posicoes(db, investidor_id, posicoes) -> None:
    db.execute(
        text(f"DELETE FROM {SCHEMA}.v2_investidor_posicoes WHERE investidor_id = :i"),
        {"i": investidor_id},
    )
    for pos in posicoes or []:
        db.execute(
            text(
                f"INSERT INTO {SCHEMA}.v2_investidor_posicoes (investidor_id, posicao) VALUES (:i, :p) "
                "ON CONFLICT (investidor_id, posicao) DO NOTHING"
            ),
            {"i": investidor_id, "p": pos},
        )


def definir_squads(db, investidor_id, squad_ids) -> None:
    db.execute(
        text(f"DELETE FROM {SCHEMA}.v2_investidor_squads WHERE investidor_id = :i"),
        {"i": investidor_id},
    )
    for sid in squad_ids or []:
        db.execute(
            text(
                f"INSERT INTO {SCHEMA}.v2_investidor_squads (investidor_id, squad_id) VALUES (:i, :s) "
                "ON CONFLICT (investidor_id, squad_id) DO NOTHING"
            ),
            {"i": investidor_id, "s": sid},
        )


# ── Helpers de sessão (usados pelo app/templates) ────────────────────────────


def aplicar_sessao(db, sessao, user) -> None:
    """Carrega os dados v2_ do usuário na sessão Flask."""
    ctx = carregar_contexto(db, user.id)
    capacidades = list(ctx["capacidades"])
    if (user.nivel_acesso or "").strip() == "Admin" and CAP_ADMIN not in capacidades:
        capacidades.append(CAP_ADMIN)

    sessao["investidor_id"] = user.id
    sessao["cargo"] = ctx["cargo"]
    sessao["posicoes"] = ctx["posicoes"]
    sessao["squads"] = ctx["squads"]
    sessao["squad_ids"] = [s["id"] for s in ctx["squads"]]
    sessao["capacidades"] = capacidades
    sessao["pode_gerenciar_feed"] = bool(ctx.get("pode_gerenciar_feed"))
    acessos = carregar_acessos(db, user.id, user.nivel_acesso)
    if getattr(user, "pode_editar_kanban", False):
        acessos["kanban"] = "editar"
    sessao["acessos_telas"] = acessos

    # Compatibilidade de exibição (valores vindos do v2_)
    sessao["funcao"] = ctx["cargo"]
    sessao["posicao"] = ctx["posicoes"][0] if ctx["posicoes"] else None
    sessao["squad"] = ctx["squads"][0]["nome"] if ctx["squads"] else None


def capacidades() -> set:
    from flask import session

    return set(session.get("capacidades") or [])


def tem(cap: str) -> bool:
    return cap in capacidades()


def is_admin() -> bool:
    from flask import session

    return (session.get("nivel_acesso") or "").strip() == "Admin"


def is_gestao_ampla() -> bool:
    return is_admin() or CAP_GESTAO_AMPLA in capacidades()


def is_gestao_squad() -> bool:
    return is_admin() or CAP_GESTAO_SQUAD in capacidades()


def is_gestao() -> bool:
    """Gestão em qualquer escopo (ampla ou por squad) ou admin."""
    return is_admin() or is_gestao_ampla() or is_gestao_squad()


def apenas_gestao_squad() -> bool:
    """Usuário cuja única forma de gestão é por squad (ex.: Coordenador)."""
    return (CAP_GESTAO_SQUAD in capacidades()) and not is_admin() and (CAP_GESTAO_AMPLA not in capacidades())


def flag_feed() -> bool:
    from flask import session

    return bool(session.get("pode_gerenciar_feed"))


def pode_criar_eventos() -> bool:
    """Criar eventos no feed: exige a flag do usuário (nem Admin/Gerência têm bypass)."""
    return flag_feed()


def pode_fixar_feed() -> bool:
    """Fixar/desfixar posts: exige a flag do usuário (nem Admin/Gerência têm bypass)."""
    return flag_feed()


# Compatibilidade: nome do cargo novo (v2_) -> nome usado nos parâmetros de
# remuneração legados (tabela remuneracao_cargos, que não foi alterada).
CARGO_REMUNERACAO_ALIAS = {
    "Account Manager": "Account",
    "Web-Designer": "Webdesigner",
    "Copy-Writter": "Copy",
}


def cargo_remuneracao(cargo: Optional[str]) -> Optional[str]:
    if not cargo:
        return cargo
    return CARGO_REMUNERACAO_ALIAS.get(cargo, cargo)


# Mapeamento de nomes de cargo/posição legados -> capacidades exigidas.
# Usado pelo decorator check_access para não reescrever todas as chamadas.
ROLE_CAPS = {
    "gerência": {CAP_GESTAO_AMPLA},
    "gerencia": {CAP_GESTAO_AMPLA},
    "sócio": {CAP_GESTAO_AMPLA},
    "socio": {CAP_GESTAO_AMPLA},
    "coordenador": {CAP_GESTAO_SQUAD},
    "account": {CAP_OPERACAO_ACCOUNT},
    "gestor de tráfego": {CAP_OPERACAO_GT},
    "gestor de trafego": {CAP_OPERACAO_GT},
    "desenvolvedor": {CAP_OPERACAO_GT},
    "designer": {CAP_CRIATIVA},
    "webdesigner": {CAP_CRIATIVA},
    "web-designer": {CAP_CRIATIVA},
    "customer success": {CAP_CS_CX},
    "cs-cx": {CAP_CS_CX},
    "cientista": {CAP_OPERACAO_ACCOUNT, CAP_OPERACAO_GT},
}


def _norm(valor: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFC", (valor or "").strip().lower())


def pode_por_roles(roles) -> bool:
    """True se o usuário possui alguma capacidade associada aos nomes dados."""
    if is_admin() or is_gestao_ampla():
        return True
    caps = capacidades()
    needed = set()
    for role in roles or []:
        needed |= ROLE_CAPS.get(_norm(role), set())
    return bool(caps & needed)



# ── Acesso por tela (usuário) ────────────────────────────────────────────────
NIVEIS_TELA = ("nenhum", "ver", "editar")
ORDEM_NIVEL_TELA = {"nenhum": 0, "ver": 1, "editar": 2}


def _nivel_max_tela(a, b):
    return a if ORDEM_NIVEL_TELA.get(a, 0) >= ORDEM_NIVEL_TELA.get(b, 0) else b


def listar_telas(db) -> List[Dict[str, Any]]:
    rows = db.execute(
        text(
            f"SELECT codigo, nome, grupo, ordem, acesso_padrao, ativo "
            f"FROM {SCHEMA}.v2_telas WHERE ativo = TRUE ORDER BY ordem, nome"
        )
    ).all()
    return [
        {"codigo": r[0], "nome": r[1], "grupo": r[2], "ordem": r[3], "acesso_padrao": r[4]}
        for r in rows
    ]


def carregar_acessos(db, investidor_id=None, nivel_acesso=None) -> Dict[str, str]:
    """Resolve o nível efetivo por tela.

    Precedência: usuário > maior(cargo, posições, padrão da tela).
    Admin recebe 'editar' em todas.
    """
    telas = listar_telas(db)
    mapa = {t["codigo"]: t["acesso_padrao"] for t in telas}

    if (nivel_acesso or "").strip() == "Admin":
        return {codigo: "editar" for codigo in mapa}

    if investidor_id:
        cargo = db.execute(
            text(f"SELECT cargo FROM {SCHEMA}.v2_investidor_cargo WHERE investidor_id = :i"),
            {"i": investidor_id},
        ).scalar()
        posicoes = [
            r[0]
            for r in db.execute(
                text(f"SELECT posicao FROM {SCHEMA}.v2_investidor_posicoes WHERE investidor_id = :i"),
                {"i": investidor_id},
            ).all()
        ]

        if cargo:
            for tela, nivel in db.execute(
                text(f"SELECT tela, nivel FROM {SCHEMA}.v2_cargo_telas WHERE cargo = :c"),
                {"c": cargo},
            ).all():
                mapa[tela] = _nivel_max_tela(mapa.get(tela, "nenhum"), nivel)
        if posicoes:
            for tela, nivel in db.execute(
                text(f"SELECT tela, nivel FROM {SCHEMA}.v2_posicao_telas WHERE posicao = ANY(:p)"),
                {"p": posicoes},
            ).all():
                mapa[tela] = _nivel_max_tela(mapa.get(tela, "nenhum"), nivel)

        # Override explícito do usuário (inclusive 'nenhum' para revogar)
        for tela, nivel in db.execute(
            text(f"SELECT tela, nivel FROM {SCHEMA}.v2_usuario_telas WHERE investidor_id = :i"),
            {"i": investidor_id},
        ).all():
            mapa[tela] = nivel
    return mapa


def _acessos_sessao() -> Dict[str, str]:
    from flask import session

    return session.get("acessos_telas") or {}


def nivel_tela(codigo: str) -> str:
    mapa = _acessos_sessao()
    if codigo in mapa:
        return mapa[codigo]
    # sessão antiga (antes do modelo de telas): calcula e guarda
    try:
        from flask import session as _s
        from database import Session

        with Session() as db:
            mapa = carregar_acessos(db, _s.get("investidor_id"), _s.get("nivel_acesso"))
        _s["acessos_telas"] = mapa
        return mapa.get(codigo, "nenhum")
    except Exception:
        return "ver" if codigo in ("feed", "perfil", "minha_agenda") else "nenhum"


def pode_tela(codigo: str, nivel: str = "ver") -> bool:
    if is_admin():
        return True
    return ORDEM_NIVEL_TELA.get(nivel_tela(codigo), 0) >= ORDEM_NIVEL_TELA.get(nivel, 1)


def pode_editar_tela(codigo: str) -> bool:
    return pode_tela(codigo, "editar")


# ── Escrita: acessos por usuário / cargo / posição ──────────────────────────


def _salvar_acessos(db, tabela, coluna, alvo, acessos):
    db.execute(
        text(f"DELETE FROM {SCHEMA}.{tabela} WHERE {coluna} = :a"), {"a": alvo}
    )
    for tela, nivel in (acessos or {}).items():
        if nivel in NIVEIS_TELA and nivel != "nenhum":
            db.execute(
                text(
                    f"INSERT INTO {SCHEMA}.{tabela} ({coluna}, tela, nivel) "
                    "VALUES (:a, :t, :n) ON CONFLICT DO NOTHING"
                ),
                {"a": alvo, "t": tela, "n": nivel},
            )


def definir_acessos_usuario(db, investidor_id, acessos):
    """Grava overrides do usuário. Níveis 'nenhum' são gravados (revogação)."""
    db.execute(
        text(f"DELETE FROM {SCHEMA}.v2_usuario_telas WHERE investidor_id = :i"),
        {"i": investidor_id},
    )
    for tela, nivel in (acessos or {}).items():
        if nivel in NIVEIS_TELA:
            db.execute(
                text(
                    f"INSERT INTO {SCHEMA}.v2_usuario_telas (investidor_id, tela, nivel) "
                    "VALUES (:i, :t, :n)"
                ),
                {"i": investidor_id, "t": tela, "n": nivel},
            )


def definir_acessos_cargo(db, cargo, acessos):
    _salvar_acessos(db, "v2_cargo_telas", "cargo", cargo, acessos)


def definir_acessos_posicao(db, posicao, acessos):
    _salvar_acessos(db, "v2_posicao_telas", "posicao", posicao, acessos)


def listar_acessos_cargo(db, cargo) -> Dict[str, str]:
    return {
        r[0]: r[1]
        for r in db.execute(
            text(f"SELECT tela, nivel FROM {SCHEMA}.v2_cargo_telas WHERE cargo = :c"),
            {"c": cargo},
        ).all()
    }


def listar_acessos_posicao(db, posicao) -> Dict[str, str]:
    return {
        r[0]: r[1]
        for r in db.execute(
            text(f"SELECT tela, nivel FROM {SCHEMA}.v2_posicao_telas WHERE posicao = :p"),
            {"p": posicao},
        ).all()
    }


def listar_acessos_usuario(db, investidor_id) -> Dict[str, str]:
    return {
        r[0]: r[1]
        for r in db.execute(
            text(f"SELECT tela, nivel FROM {SCHEMA}.v2_usuario_telas WHERE investidor_id = :i"),
            {"i": investidor_id},
        ).all()
    }


# ── CRUD de cargos / posições ───────────────────────────────────────────────


def _crud_tabela(db, tabela, acao, nome, novo=None):
    if tabela not in ("v2_cargos", "v2_posicoes"):
        raise ValueError("Catálogo inválido.")
    if acao == "criar":
        db.execute(
            text(
                f"INSERT INTO {SCHEMA}.{tabela} (nome, ativo, ordem) "
                f"VALUES (:n, TRUE, (SELECT COALESCE(MAX(ordem),0)+1 FROM {SCHEMA}.{tabela})) "
                "ON CONFLICT (nome) DO UPDATE SET ativo = TRUE"
            ),
            {"n": nome},
        )
    elif acao == "renomear" and novo:
        db.execute(
            text(f"UPDATE {SCHEMA}.{tabela} SET nome = :novo WHERE nome = :n"),
            {"novo": novo, "n": nome},
        )
    elif acao == "desativar":
        db.execute(
            text(f"UPDATE {SCHEMA}.{tabela} SET ativo = FALSE WHERE nome = :n"),
            {"n": nome},
        )
    elif acao == "ativar":
        db.execute(
            text(f"UPDATE {SCHEMA}.{tabela} SET ativo = TRUE WHERE nome = :n"),
            {"n": nome},
        )


def criar_cargo(db, nome):
    _crud_tabela(db, "v2_cargos", "criar", nome)


def criar_posicao(db, nome):
    _crud_tabela(db, "v2_posicoes", "criar", nome)


def renomear_cargo(db, nome, novo):
    _crud_tabela(db, "v2_cargos", "renomear", nome, novo)


def renomear_posicao(db, nome, novo):
    _crud_tabela(db, "v2_posicoes", "renomear", nome, novo)


def desativar_cargo(db, nome):
    _crud_tabela(db, "v2_cargos", "desativar", nome)


def desativar_posicao(db, nome):
    _crud_tabela(db, "v2_posicoes", "desativar", nome)
