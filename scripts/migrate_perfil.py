"""Migration: adiciona a coluna data_admissao ao cadastro de investidores.

Usage:
    python scripts/migrate_perfil.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

SCHEMA = "plataforma_geral"
TABELA = f"{SCHEMA}.investidores"

COLUNAS = [
    ("data_admissao", "DATE"),
]


def migrate():
    print("Adicionando coluna data_admissao em investidores...")
    with engine.begin() as conn:
        for nome, tipo in COLUNAS:
            conn.execute(text(f"ALTER TABLE {TABELA} ADD COLUMN IF NOT EXISTS {nome} {tipo}"))
    print("Coluna garantida com sucesso.")


if __name__ == "__main__":
    migrate()