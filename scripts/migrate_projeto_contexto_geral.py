"""Migration: documento do projeto (context.md) no contexto versionado.

Adiciona a coluna TEXT ``contexto_geral`` em ``projetos_contexto``.
Idempotente.

Usage:
    python scripts/migrate_projeto_contexto_geral.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

SCHEMA = "plataforma_geral"


def migrate():
    with engine.begin() as conn:
        print("Adicionando coluna contexto_geral em projetos_contexto...")
        conn.execute(text(
            f'ALTER TABLE "{SCHEMA}".projetos_contexto '
            "ADD COLUMN IF NOT EXISTS contexto_geral TEXT"
        ))
    print("Migração do documento do projeto concluída.")


if __name__ == "__main__":
    migrate()