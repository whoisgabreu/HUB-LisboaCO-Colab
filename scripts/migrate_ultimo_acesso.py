"""Migration: adiciona a coluna ultimo_acesso em investidores (dias sem logar).

Usage:
    python scripts/migrate_ultimo_acesso.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

SCHEMA = "plataforma_geral"
TABELA = f"{SCHEMA}.investidores"


def migrate():
    print("Adicionando coluna ultimo_acesso em investidores...")
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {TABELA} ADD COLUMN IF NOT EXISTS ultimo_acesso TIMESTAMPTZ"))
    print("Coluna garantida com sucesso.")


if __name__ == "__main__":
    migrate()