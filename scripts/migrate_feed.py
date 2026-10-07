"""
Migration script: Feed social do HUB.

Cria as tabelas do feed (posts, reações e comentários) e adiciona a coluna
``data_nascimento`` em ``plataforma_geral.investidores``.

Run with: python scripts/migrate_feed.py
"""
import sys

sys.path.insert(0, ".")

from sqlalchemy import text

from database import engine


def column_exists(connection, table_name, column_name, schema="plataforma_geral"):
    result = connection.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table AND column_name = :column)"
        ),
        {"schema": schema, "table": table_name, "column": column_name},
    ).scalar()
    return result


def table_exists(connection, table_name, schema="plataforma_geral"):
    result = connection.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_name = :table)"
        ),
        {"schema": schema, "table": table_name},
    ).scalar()
    return result


def run_migration():
    print("[Migration] Criando estrutura do feed social...")

    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS plataforma_geral"))

        # ── data_nascimento em investidores ───────────────────────────────────
        if not column_exists(conn, "investidores", "data_nascimento"):
            conn.execute(
                text(
                    "ALTER TABLE plataforma_geral.investidores "
                    "ADD COLUMN data_nascimento DATE"
                )
            )
            print("[Migration] Coluna investidores.data_nascimento criada.")
        else:
            print("[Migration] Coluna investidores.data_nascimento já existe.")

        # ── feed_posts ────────────────────────────────────────────────────────
        if not table_exists(conn, "feed_posts"):
            conn.execute(
                text(
                    """
                    CREATE TABLE plataforma_geral.feed_posts (
                        id SERIAL PRIMARY KEY,
                        autor_email VARCHAR(255),
                        tipo VARCHAR(20) NOT NULL DEFAULT 'post',
                        titulo VARCHAR(200),
                        conteudo TEXT,
                        evento_data TIMESTAMP,
                        evento_local VARCHAR(200),
                        fixado BOOLEAN NOT NULL DEFAULT FALSE,
                        fixado_ate TIMESTAMP,
                        deletado BOOLEAN NOT NULL DEFAULT FALSE,
                        criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                        atualizado_em TIMESTAMP
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_feed_posts_criado_em "
                    "ON plataforma_geral.feed_posts(criado_em DESC)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_feed_posts_fixado "
                    "ON plataforma_geral.feed_posts(fixado, fixado_ate)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_feed_posts_autor "
                    "ON plataforma_geral.feed_posts(autor_email)"
                )
            )
            print("[Migration] Tabela feed_posts criada.")
        else:
            print("[Migration] Tabela feed_posts já existe.")

        # ── feed_reacoes ──────────────────────────────────────────────────────
        if not table_exists(conn, "feed_reacoes"):
            conn.execute(
                text(
                    """
                    CREATE TABLE plataforma_geral.feed_reacoes (
                        id SERIAL PRIMARY KEY,
                        post_id INTEGER NOT NULL REFERENCES plataforma_geral.feed_posts(id) ON DELETE CASCADE,
                        usuario_email VARCHAR(255) NOT NULL,
                        tipo VARCHAR(20) NOT NULL,
                        criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                        CONSTRAINT uq_feed_reacao_usuario UNIQUE (post_id, usuario_email)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_feed_reacoes_post "
                    "ON plataforma_geral.feed_reacoes(post_id)"
                )
            )
            print("[Migration] Tabela feed_reacoes criada.")
        else:
            print("[Migration] Tabela feed_reacoes já existe.")

        # ── feed_comentarios ──────────────────────────────────────────────────
        if not table_exists(conn, "feed_comentarios"):
            conn.execute(
                text(
                    """
                    CREATE TABLE plataforma_geral.feed_comentarios (
                        id SERIAL PRIMARY KEY,
                        post_id INTEGER NOT NULL REFERENCES plataforma_geral.feed_posts(id) ON DELETE CASCADE,
                        parent_id INTEGER REFERENCES plataforma_geral.feed_comentarios(id) ON DELETE CASCADE,
                        autor_email VARCHAR(255) NOT NULL,
                        conteudo TEXT NOT NULL,
                        deletado BOOLEAN NOT NULL DEFAULT FALSE,
                        criado_em TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_feed_comentarios_post "
                    "ON plataforma_geral.feed_comentarios(post_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_feed_comentarios_parent "
                    "ON plataforma_geral.feed_comentarios(parent_id)"
                )
            )
            print("[Migration] Tabela feed_comentarios criada.")
        else:
            print("[Migration] Tabela feed_comentarios já existe.")

        conn.commit()

    print("[Migration] Estrutura do feed verificada/criada com sucesso.")


if __name__ == "__main__":
    run_migration()
