"""
Migration script: Create user_faces and face_auth_log tables.
Run with: python scripts/migrate_face_auth.py
"""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text, inspect
from database import engine, Session
from models import Base, UserFace, FaceAuthLog


def table_exists(connection, table_name, schema="plataforma_geral"):
    result = connection.execute(
        text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = :schema AND table_name = :table)"),
        {"schema": schema, "table": table_name}
    ).scalar()
    return result


def run_migration():
    print("[Migration] Criando tabelas de autenticação facial...")

    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS plataforma_geral"))
        conn.commit()

        user_faces_exists = table_exists(conn, "user_faces")
        face_auth_log_exists = table_exists(conn, "face_auth_log")

        if not user_faces_exists:
            conn.execute(text("""
                CREATE TABLE plataforma_geral.user_faces (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES plataforma_geral.investidores(id) ON DELETE CASCADE,
                    embedding JSONB NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    samples INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_user_faces_user_id ON plataforma_geral.user_faces(user_id)"))
            conn.execute(text("CREATE INDEX idx_user_faces_active ON plataforma_geral.user_faces(is_active)"))
            print("[Migration] Tabela user_faces criada com sucesso.")
        else:
            print("[Migration] Tabela user_faces já existe.")

        if not face_auth_log_exists:
            conn.execute(text("""
                CREATE TABLE plataforma_geral.face_auth_log (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    email VARCHAR(100),
                    event_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    similarity VARCHAR(20),
                    samples INTEGER,
                    ip_address VARCHAR(50),
                    user_agent VARCHAR(500),
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX idx_face_auth_log_email ON plataforma_geral.face_auth_log(email)"))
            conn.execute(text("CREATE INDEX idx_face_auth_log_event ON plataforma_geral.face_auth_log(event_type)"))
            conn.execute(text("CREATE INDEX idx_face_auth_log_created ON plataforma_geral.face_auth_log(created_at)"))
            print("[Migration] Tabela face_auth_log criada com sucesso.")
        else:
            print("[Migration] Tabela face_auth_log já existe.")

        conn.commit()

    print("[Migration] Tabelas de autenticação facial verificadas/criadas com sucesso.")


if __name__ == "__main__":
    run_migration()
