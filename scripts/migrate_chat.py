"""
Migration script: Chat interno do HUB (1:1).

Cria as tabelas de conversas, mensagens, leituras e presença.

Run with: python scripts/migrate_chat.py
"""
import sys

sys.path.insert(0, ".")

from sqlalchemy import text

from database import engine

SCHEMA = "plataforma_geral"


def table_exists(connection, table_name, schema=SCHEMA):
    return connection.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_name = :table)"
        ),
        {"schema": schema, "table": table_name},
    ).scalar()


def run_migration():
    print("[Migration] Chat interno...")

    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))

        if not table_exists(conn, "chat_conversas"):
            conn.execute(
                text(
                    f"""
                    CREATE TABLE {SCHEMA}.chat_conversas (
                        id SERIAL PRIMARY KEY,
                        user_a VARCHAR(255) NOT NULL,
                        user_b VARCHAR(255) NOT NULL,
                        criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                        ultima_mensagem_em TIMESTAMP,
                        CONSTRAINT uq_chat_conversa_par UNIQUE (user_a, user_b)
                    )
                    """
                )
            )
            conn.execute(text(f"CREATE INDEX idx_chat_conv_a ON {SCHEMA}.chat_conversas(user_a)"))
            conn.execute(text(f"CREATE INDEX idx_chat_conv_b ON {SCHEMA}.chat_conversas(user_b)"))
            print("[Migration] Tabela chat_conversas criada.")
        else:
            print("[Migration] Tabela chat_conversas já existe.")

        if not table_exists(conn, "chat_mensagens"):
            conn.execute(
                text(
                    f"""
                    CREATE TABLE {SCHEMA}.chat_mensagens (
                        id BIGSERIAL PRIMARY KEY,
                        conversa_id INTEGER NOT NULL REFERENCES {SCHEMA}.chat_conversas(id) ON DELETE CASCADE,
                        autor_email VARCHAR(255) NOT NULL,
                        conteudo TEXT NOT NULL,
                        deletado BOOLEAN NOT NULL DEFAULT FALSE,
                        editado BOOLEAN NOT NULL DEFAULT FALSE,
                        editado_em TIMESTAMP,
                        criado_em TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            conn.execute(text(f"CREATE INDEX idx_chat_msg_conv ON {SCHEMA}.chat_mensagens(conversa_id, id DESC)"))
            print("[Migration] Tabela chat_mensagens criada.")
        else:
            print("[Migration] Tabela chat_mensagens já existe.")

        if not table_exists(conn, "chat_leituras"):
            conn.execute(
                text(
                    f"""
                    CREATE TABLE {SCHEMA}.chat_leituras (
                        id SERIAL PRIMARY KEY,
                        conversa_id INTEGER NOT NULL REFERENCES {SCHEMA}.chat_conversas(id) ON DELETE CASCADE,
                        usuario_email VARCHAR(255) NOT NULL,
                        ultima_lida_msg_id BIGINT NOT NULL DEFAULT 0,
                        ultima_lida_em TIMESTAMP,
                        CONSTRAINT uq_chat_leitura UNIQUE (conversa_id, usuario_email)
                    )
                    """
                )
            )
            print("[Migration] Tabela chat_leituras criada.")
        else:
            print("[Migration] Tabela chat_leituras já existe.")

        if not table_exists(conn, "chat_presenca"):
            conn.execute(
                text(
                    f"""
                    CREATE TABLE {SCHEMA}.chat_presenca (
                        usuario_email VARCHAR(255) PRIMARY KEY,
                        ultimo_ping TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            print("[Migration] Tabela chat_presenca criada.")
        else:
            print("[Migration] Tabela chat_presenca já existe.")

        conn.commit()

    print("[Migration] Chat interno concluído.")


if __name__ == "__main__":
    run_migration()
