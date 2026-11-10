"""Migration: auditoria criptografada do Desabafo.

Mantém os posts públicos anônimos e cria uma tabela separada com o ciphertext
Para auditoria restrita. O ciphertext não é exposto pela API.

Usage:
    python scripts/migrate_desabafo_audit.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

SCHEMA = "plataforma_geral"


def migrate():
    with engine.begin() as conn:
        conn.execute(text(
            f'CREATE TABLE IF NOT EXISTS "{SCHEMA}".desabafo_audit ('
            "id BIGSERIAL PRIMARY KEY, "
            "post_id INTEGER NOT NULL, "
            "audit_ref TEXT NOT NULL, "
            "ciphertext BYTEA NOT NULL, "
            "key_id TEXT, "
            "created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        ))
        conn.execute(text(
            f'CREATE UNIQUE INDEX IF NOT EXISTS uq_desabafo_audit_ref '
            f'ON "{SCHEMA}".desabafo_audit (audit_ref)'
        ))
        conn.execute(text(
            f'CREATE INDEX IF NOT EXISTS desabafo_audit_post_idx '
            f'ON "{SCHEMA}".desabafo_audit (post_id)'
        ))
        conn.execute(text(
            f'ALTER TABLE "{SCHEMA}".desabafo_posts '
            "ADD COLUMN IF NOT EXISTS audit_ref TEXT"
        ))
        conn.execute(text(
            f'CREATE UNIQUE INDEX IF NOT EXISTS uq_desabafo_posts_audit_ref '
            f'ON "{SCHEMA}".desabafo_posts (audit_ref) '
            "WHERE audit_ref IS NOT NULL"
        ))

    print("Migração da auditoria do Desabafo concluída.")


if __name__ == "__main__":
    migrate()
