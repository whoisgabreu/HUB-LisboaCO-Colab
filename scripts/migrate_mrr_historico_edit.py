"""Migration: adiciona colunas de edição manual ao histórico de MRR.

Usage:
    python scripts/migrate_mrr_historico_edit.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

SCHEMA = "plataforma_geral"
TABELA = f"{SCHEMA}.projeto_mrr_historico"

COLUNAS = [
    ("manual", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("editado_em", "TIMESTAMP"),
    ("editado_por", "VARCHAR(255)"),
    ("observacao", "TEXT"),
]


def migrate():
    print("Ajustando colunas de edição do histórico de MRR...")
    with engine.begin() as conn:
        for nome, tipo in COLUNAS:
            conn.execute(text(f"ALTER TABLE {TABELA} ADD COLUMN IF NOT EXISTS {nome} {tipo}"))
    print("Colunas garantidas com sucesso.")


if __name__ == "__main__":
    migrate()
