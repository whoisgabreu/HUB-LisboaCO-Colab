"""
Migration script: HUB v2.

Cria as estruturas novas com prefixo ``v2_`` em ``plataforma_geral`` (cargos,
posições, capacidades, squads e vínculos) e popula a partir dos dados legados.

Princípios:
- NÃO altera nenhuma tabela/coluna de produção (só lê o legado).
- Idempotente: pode ser reexecutado com segurança.

Run with: python scripts/migrate_v2.py
"""
import sys

sys.path.insert(0, ".")

from sqlalchemy import text

from database import engine

SCHEMA = "plataforma_geral"

# ── Catálogos ────────────────────────────────────────────────────────────────

CARGOS = [
    "Diretor",
    "Financeiro",
    "Gerente",
    "Gestor de Projeto",
    "Account Manager",
    "Gestor de Tráfego",
    "Designer",
    "Web-Designer",
    "CS-CX",
    "RH",
    "Desenvolvedor",
    "Assistente",
    "Copy-Writter",
]

POSICOES = ["Gerência", "Sócio", "Coordenador", "Operação", "Tech", "People"]

CAPACIDADES = [
    ("admin", "Administrador (via nivel_acesso)"),
    ("gestao_ampla", "Gestão ampla (bypass de escopo)"),
    ("gestao_squad", "Gestão com escopo por squad"),
    ("operacao_account", "Operação - Account"),
    ("operacao_gt", "Operação - Gestor de Tráfego"),
    ("criativa", "Entregas Criativas"),
    ("cs_cx", "CS / CX"),
    ("tech", "Tecnologia"),
    ("people", "People / RH"),
]

POSICAO_CAPACIDADES = {
    "Gerência": ["gestao_ampla"],
    "Sócio": ["gestao_ampla"],
    "Coordenador": ["gestao_squad"],
    "Operação": ["operacao_account", "operacao_gt"],
    "Tech": ["tech"],
    "People": ["people"],
}

CARGO_CAPACIDADES = {
    "Account Manager": ["operacao_account"],
    "Gestor de Projeto": ["operacao_account"],
    "Gestor de Tráfego": ["operacao_gt"],
    "Desenvolvedor": ["operacao_gt"],
    "Designer": ["criativa"],
    "Web-Designer": ["criativa"],
    "CS-CX": ["cs_cx"],
}

# Renomeação de cargos legados -> novos (somente nos dados v2_)
CARGO_MAP = {
    "Account": "Account Manager",
    "Webdesigner": "Web-Designer",
    "WebDesigner": "Web-Designer",
    "Copy": "Copy-Writter",
}

# Squads legadas que devem existir mesmo que não apareçam nos vínculos atuais.
# Obs.: "Tigers" foi unificada em "Phoenix" (rebrand) — não semear novamente.
SQUADS_EXTRA = ["Gerência", "Strike Force", "Shark", "Phoenix"]


def _scalar(conn, sql, **params):
    return conn.execute(text(sql), params).scalar()


def _table_exists(conn, table):
    return _scalar(
        conn,
        "SELECT EXISTS (SELECT FROM information_schema.tables "
        "WHERE table_schema = :s AND table_name = :t)",
        s=SCHEMA,
        t=table,
    )


def _create_tables(conn):
    ddl = [
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.v2_cargos (
            nome VARCHAR(80) PRIMARY KEY,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            ordem INTEGER NOT NULL DEFAULT 0
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.v2_posicoes (
            nome VARCHAR(80) PRIMARY KEY,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            ordem INTEGER NOT NULL DEFAULT 0
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.v2_capacidades (
            codigo VARCHAR(40) PRIMARY KEY,
            descricao VARCHAR(200),
            ordem INTEGER NOT NULL DEFAULT 0
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.v2_squads (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL UNIQUE,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            ordem INTEGER NOT NULL DEFAULT 0
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.v2_investidor_cargo (
            investidor_id INTEGER PRIMARY KEY,
            cargo VARCHAR(80),
            atualizado_em TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.v2_investidor_posicoes (
            id SERIAL PRIMARY KEY,
            investidor_id INTEGER NOT NULL,
            posicao VARCHAR(80) NOT NULL,
            CONSTRAINT uq_v2_inv_pos UNIQUE (investidor_id, posicao)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.v2_investidor_squads (
            id SERIAL PRIMARY KEY,
            investidor_id INTEGER NOT NULL,
            squad_id INTEGER NOT NULL,
            CONSTRAINT uq_v2_inv_squad UNIQUE (investidor_id, squad_id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.v2_projeto_squads (
            id SERIAL PRIMARY KEY,
            pipefy_id INTEGER NOT NULL,
            squad_id INTEGER NOT NULL,
            CONSTRAINT uq_v2_proj_squad UNIQUE (pipefy_id, squad_id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.v2_posicao_capacidades (
            posicao VARCHAR(80) NOT NULL,
            capacidade VARCHAR(40) NOT NULL,
            CONSTRAINT uq_v2_pos_cap UNIQUE (posicao, capacidade)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.v2_cargo_capacidades (
            cargo VARCHAR(80) NOT NULL,
            capacidade VARCHAR(40) NOT NULL,
            CONSTRAINT uq_v2_cargo_cap UNIQUE (cargo, capacidade)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.v2_investidor_flags (
            investidor_id INTEGER PRIMARY KEY,
            pode_gerenciar_feed BOOLEAN NOT NULL DEFAULT FALSE
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.v2_config (
            chave VARCHAR(100) PRIMARY KEY,
            valor TEXT
        )
        """,
    ]
    for stmt in ddl:
        conn.execute(text(stmt))
    conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_v2_inv_pos_inv ON {SCHEMA}.v2_investidor_posicoes(investidor_id)"))
    conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_v2_inv_squad_inv ON {SCHEMA}.v2_investidor_squads(investidor_id)"))
    conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_v2_proj_squad_proj ON {SCHEMA}.v2_projeto_squads(pipefy_id)"))


def _seed_catalogos(conn):
    for i, nome in enumerate(CARGOS):
        conn.execute(
            text(
                f"INSERT INTO {SCHEMA}.v2_cargos (nome, ativo, ordem) VALUES (:n, TRUE, :o) "
                "ON CONFLICT (nome) DO UPDATE SET ordem = EXCLUDED.ordem"
            ),
            {"n": nome, "o": i},
        )
    for i, nome in enumerate(POSICOES):
        conn.execute(
            text(
                f"INSERT INTO {SCHEMA}.v2_posicoes (nome, ativo, ordem) VALUES (:n, TRUE, :o) "
                "ON CONFLICT (nome) DO UPDATE SET ordem = EXCLUDED.ordem"
            ),
            {"n": nome, "o": i},
        )
    for i, (codigo, desc) in enumerate(CAPACIDADES):
        conn.execute(
            text(
                f"INSERT INTO {SCHEMA}.v2_capacidades (codigo, descricao, ordem) VALUES (:c, :d, :o) "
                "ON CONFLICT (codigo) DO UPDATE SET descricao = EXCLUDED.descricao, ordem = EXCLUDED.ordem"
            ),
            {"c": codigo, "d": desc, "o": i},
        )
    for posicao, caps in POSICAO_CAPACIDADES.items():
        for cap in caps:
            conn.execute(
                text(
                    f"INSERT INTO {SCHEMA}.v2_posicao_capacidades (posicao, capacidade) VALUES (:p, :c) "
                    "ON CONFLICT (posicao, capacidade) DO NOTHING"
                ),
                {"p": posicao, "c": cap},
            )
    for cargo, caps in CARGO_CAPACIDADES.items():
        for cap in caps:
            conn.execute(
                text(
                    f"INSERT INTO {SCHEMA}.v2_cargo_capacidades (cargo, capacidade) VALUES (:c, :ca) "
                    "ON CONFLICT (cargo, capacidade) DO NOTHING"
                ),
                {"c": cargo, "ca": cap},
            )


def _seed_squads(conn):
    nomes = set(SQUADS_EXTRA)
    for row in conn.execute(text(f"SELECT DISTINCT squad FROM {SCHEMA}.investidores WHERE squad IS NOT NULL AND squad <> ''")).all():
        nomes.add(row[0])
    for row in conn.execute(text(f"SELECT DISTINCT squad_atribuida FROM {SCHEMA}.projetos WHERE squad_atribuida IS NOT NULL AND squad_atribuida <> ''")).all():
        nomes.add(row[0])
    if _table_exists(conn, "squads"):
        for row in conn.execute(text(f"SELECT DISTINCT nome FROM {SCHEMA}.squads WHERE nome IS NOT NULL AND nome <> ''")).all():
            nomes.add(row[0])

    # Normalização de rebrand: "Tigers" -> "Phoenix"
    if "Tigers" in nomes:
        nomes.discard("Tigers")
        nomes.add("Phoenix")

    for i, nome in enumerate(sorted(nomes)):
        conn.execute(
            text(
                f"INSERT INTO {SCHEMA}.v2_squads (nome, ativo, ordem) VALUES (:n, TRUE, :o) "
                "ON CONFLICT (nome) DO UPDATE SET ordem = EXCLUDED.ordem"
            ),
            {"n": nome, "o": i},
        )


def _populate_vinculos(conn):
    # cargo por investidor (com rename)
    inv = conn.execute(
        text(f"SELECT id, funcao FROM {SCHEMA}.investidores WHERE funcao IS NOT NULL AND funcao <> ''")
    ).all()
    for inv_id, funcao in inv:
        cargo = CARGO_MAP.get(funcao, funcao)
        conn.execute(
            text(
                f"INSERT INTO {SCHEMA}.v2_investidor_cargo (investidor_id, cargo, atualizado_em) "
                "VALUES (:i, :c, NOW()) ON CONFLICT (investidor_id) DO UPDATE SET cargo = EXCLUDED.cargo, atualizado_em = NOW()"
            ),
            {"i": inv_id, "c": cargo},
        )

    # posicoes por investidor (valor escalar legado; suporta separadores por segurança)
    pos = conn.execute(
        text(f"SELECT id, posicao FROM {SCHEMA}.investidores WHERE posicao IS NOT NULL AND posicao <> ''")
    ).all()
    for inv_id, posicao in pos:
        partes = [p.strip() for p in str(posicao).replace(";", ",").split(",") if p.strip()]
        for parte in partes:
            conn.execute(
                text(
                    f"INSERT INTO {SCHEMA}.v2_investidor_posicoes (investidor_id, posicao) VALUES (:i, :p) "
                    "ON CONFLICT (investidor_id, posicao) DO NOTHING"
                ),
                {"i": inv_id, "p": parte},
            )

    # squads por investidor (nome -> id)
    conn.execute(
        text(
            f"""
            INSERT INTO {SCHEMA}.v2_investidor_squads (investidor_id, squad_id)
            SELECT i.id, s.id
            FROM {SCHEMA}.investidores i
            JOIN {SCHEMA}.v2_squads s ON s.nome = i.squad
            WHERE i.squad IS NOT NULL AND i.squad <> ''
            ON CONFLICT (investidor_id, squad_id) DO NOTHING
            """
        )
    )

    # squads por projeto (nome -> id)
    conn.execute(
        text(
            f"""
            INSERT INTO {SCHEMA}.v2_projeto_squads (pipefy_id, squad_id)
            SELECT p.pipefy_id, s.id
            FROM {SCHEMA}.projetos p
            JOIN {SCHEMA}.v2_squads s ON s.nome = p.squad_atribuida
            WHERE p.squad_atribuida IS NOT NULL AND p.squad_atribuida <> ''
            ON CONFLICT (pipefy_id, squad_id) DO NOTHING
            """
        )
    )


def _seed_config(conn):
    """Configurações gerais (key/value)."""
    defaults = {
        "feed_sistema_nome": "HUB (Sistema)",
        "feed_sistema_icone": "fa-robot",
    }
    for chave, valor in defaults.items():
        conn.execute(
            text(
                f"INSERT INTO {SCHEMA}.v2_config (chave, valor) VALUES (:c, :v) "
                "ON CONFLICT (chave) DO NOTHING"
            ),
            {"c": chave, "v": valor},
        )


def run_migration():
    print("[Migration v2] Iniciando...")
    with engine.begin() as conn:
        _create_tables(conn)
        _seed_catalogos(conn)
        _seed_squads(conn)
        _populate_vinculos(conn)
        _seed_config(conn)

        # Posts automáticos de aniversário passam a ter autoria do "sistema"
        if _table_exists(conn, "feed_posts"):
            n = conn.execute(
                text(
                    f"UPDATE {SCHEMA}.feed_posts SET autor_email = 'sistema' "
                    "WHERE tipo = 'aniversario' AND (autor_email IS NULL OR autor_email <> 'sistema')"
                )
            ).rowcount
            if n:
                print(f"[Migration] posts de aniversário -> autor 'sistema': {n}")

        resumo = {
            "v2_cargos": _scalar(conn, f"SELECT COUNT(*) FROM {SCHEMA}.v2_cargos"),
            "v2_posicoes": _scalar(conn, f"SELECT COUNT(*) FROM {SCHEMA}.v2_posicoes"),
            "v2_capacidades": _scalar(conn, f"SELECT COUNT(*) FROM {SCHEMA}.v2_capacidades"),
            "v2_squads": _scalar(conn, f"SELECT COUNT(*) FROM {SCHEMA}.v2_squads"),
            "v2_investidor_cargo": _scalar(conn, f"SELECT COUNT(*) FROM {SCHEMA}.v2_investidor_cargo"),
            "v2_investidor_posicoes": _scalar(conn, f"SELECT COUNT(*) FROM {SCHEMA}.v2_investidor_posicoes"),
            "v2_investidor_squads": _scalar(conn, f"SELECT COUNT(*) FROM {SCHEMA}.v2_investidor_squads"),
            "v2_projeto_squads": _scalar(conn, f"SELECT COUNT(*) FROM {SCHEMA}.v2_projeto_squads"),
            "v2_posicao_capacidades": _scalar(conn, f"SELECT COUNT(*) FROM {SCHEMA}.v2_posicao_capacidades"),
            "v2_cargo_capacidades": _scalar(conn, f"SELECT COUNT(*) FROM {SCHEMA}.v2_cargo_capacidades"),
        }
    print("[Migration v2] Concluído.")
    for k, v in resumo.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    run_migration()
