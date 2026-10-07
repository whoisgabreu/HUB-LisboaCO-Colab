"""
Migration script: Feed social V2 (recursos sociais).

Adiciona colunas em ``plataforma_geral.feed_posts`` e cria as tabelas de
notificações, enquetes, salvos, reações de comentário, denúncias e edições.

Run with: python scripts/migrate_feed_social.py
"""
import sys

sys.path.insert(0, ".")

from sqlalchemy import text

from database import engine

SCHEMA = "plataforma_geral"


def column_exists(connection, table_name, column_name, schema=SCHEMA):
    return connection.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table AND column_name = :column)"
        ),
        {"schema": schema, "table": table_name, "column": column_name},
    ).scalar()


def table_exists(connection, table_name, schema=SCHEMA):
    return connection.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_name = :table)"
        ),
        {"schema": schema, "table": table_name},
    ).scalar()


def _add_columns(conn, table, columns):
    for name, ddl in columns:
        if not column_exists(conn, table, name):
            conn.execute(text(f"ALTER TABLE {SCHEMA}.{table} ADD COLUMN {name} {ddl}"))
            print(f"[Migration] {table}.{name} criada.")
        else:
            print(f"[Migration] {table}.{name} já existe.")


def run_migration():
    print("[Migration] Feed social V2...")

    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))

        _add_columns(
            conn,
            "feed_posts",
            [
                ("visibilidade", "VARCHAR(20) NOT NULL DEFAULT 'todos'"),
                ("original_post_id", "INTEGER"),
                ("enquete", "JSONB"),
                ("editado", "BOOLEAN NOT NULL DEFAULT FALSE"),
                ("total_edicoes", "INTEGER NOT NULL DEFAULT 0"),
                ("editado_em", "TIMESTAMP"),
                ("oculto", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ],
        )

        if not table_exists(conn, "feed_notificacoes"):
            conn.execute(
                text(
                    f"""
                    CREATE TABLE {SCHEMA}.feed_notificacoes (
                        id SERIAL PRIMARY KEY,
                        usuario_email VARCHAR(255) NOT NULL,
                        tipo VARCHAR(30) NOT NULL,
                        ator_email VARCHAR(255),
                        post_id INTEGER,
                        comentario_id INTEGER,
                        texto VARCHAR(400),
                        lida BOOLEAN NOT NULL DEFAULT FALSE,
                        criado_em TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            conn.execute(text(f"CREATE INDEX idx_feed_notif_usuario ON {SCHEMA}.feed_notificacoes(usuario_email, lida)"))
            conn.execute(text(f"CREATE INDEX idx_feed_notif_criado ON {SCHEMA}.feed_notificacoes(criado_em DESC)"))
            print("[Migration] Tabela feed_notificacoes criada.")
        else:
            print("[Migration] Tabela feed_notificacoes já existe.")

        if not table_exists(conn, "feed_enquete_votos"):
            conn.execute(
                text(
                    f"""
                    CREATE TABLE {SCHEMA}.feed_enquete_votos (
                        id SERIAL PRIMARY KEY,
                        post_id INTEGER NOT NULL REFERENCES {SCHEMA}.feed_posts(id) ON DELETE CASCADE,
                        usuario_email VARCHAR(255) NOT NULL,
                        opcao_index INTEGER NOT NULL,
                        criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                        CONSTRAINT uq_feed_enquete_voto UNIQUE (post_id, usuario_email)
                    )
                    """
                )
            )
            print("[Migration] Tabela feed_enquete_votos criada.")
        else:
            print("[Migration] Tabela feed_enquete_votos já existe.")

        if not table_exists(conn, "feed_salvos"):
            conn.execute(
                text(
                    f"""
                    CREATE TABLE {SCHEMA}.feed_salvos (
                        id SERIAL PRIMARY KEY,
                        usuario_email VARCHAR(255) NOT NULL,
                        post_id INTEGER NOT NULL REFERENCES {SCHEMA}.feed_posts(id) ON DELETE CASCADE,
                        criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                        CONSTRAINT uq_feed_salvo UNIQUE (usuario_email, post_id)
                    )
                    """
                )
            )
            print("[Migration] Tabela feed_salvos criada.")
        else:
            print("[Migration] Tabela feed_salvos já existe.")

        if not table_exists(conn, "feed_comentario_reacoes"):
            conn.execute(
                text(
                    f"""
                    CREATE TABLE {SCHEMA}.feed_comentario_reacoes (
                        id SERIAL PRIMARY KEY,
                        comentario_id INTEGER NOT NULL REFERENCES {SCHEMA}.feed_comentarios(id) ON DELETE CASCADE,
                        usuario_email VARCHAR(255) NOT NULL,
                        tipo VARCHAR(20) NOT NULL,
                        criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                        CONSTRAINT uq_feed_coment_reacao UNIQUE (comentario_id, usuario_email)
                    )
                    """
                )
            )
            print("[Migration] Tabela feed_comentario_reacoes criada.")
        else:
            print("[Migration] Tabela feed_comentario_reacoes já existe.")

        if not table_exists(conn, "feed_denuncias"):
            conn.execute(
                text(
                    f"""
                    CREATE TABLE {SCHEMA}.feed_denuncias (
                        id SERIAL PRIMARY KEY,
                        post_id INTEGER NOT NULL REFERENCES {SCHEMA}.feed_posts(id) ON DELETE CASCADE,
                        usuario_email VARCHAR(255) NOT NULL,
                        motivo TEXT,
                        criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                        CONSTRAINT uq_feed_denuncia UNIQUE (post_id, usuario_email)
                    )
                    """
                )
            )
            print("[Migration] Tabela feed_denuncias criada.")
        else:
            print("[Migration] Tabela feed_denuncias já existe.")

        if not table_exists(conn, "feed_posts_edicoes"):
            conn.execute(
                text(
                    f"""
                    CREATE TABLE {SCHEMA}.feed_posts_edicoes (
                        id SERIAL PRIMARY KEY,
                        post_id INTEGER NOT NULL REFERENCES {SCHEMA}.feed_posts(id) ON DELETE CASCADE,
                        conteudo_anterior TEXT,
                        editado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                        editado_por VARCHAR(255)
                    )
                    """
                )
            )
            conn.execute(text(f"CREATE INDEX idx_feed_edicoes_post ON {SCHEMA}.feed_posts_edicoes(post_id)"))
            print("[Migration] Tabela feed_posts_edicoes criada.")
        else:
            print("[Migration] Tabela feed_posts_edicoes já existe.")

        conn.commit()

    print("[Migration] Feed social V2 concluído.")


if __name__ == "__main__":
    run_migration()
