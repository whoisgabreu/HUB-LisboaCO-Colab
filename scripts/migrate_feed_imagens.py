"""Migration: imagens nas publicações do feed.

Adiciona a coluna JSONB ``imagens`` em ``feed_posts`` (lista de objetos
``{arquivo, largura, altura}``). Idempotente.

Usage:
    python scripts/migrate_feed_imagens.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

SCHEMA = "plataforma_geral"


def migrate():
    with engine.begin() as conn:
        print("Adicionando coluna imagens em feed_posts...")
        conn.execute(text(
            f'ALTER TABLE "{SCHEMA}".feed_posts '
            "ADD COLUMN IF NOT EXISTS imagens JSONB NOT NULL DEFAULT '[]'::jsonb"
        ))
    print("Migração de imagens do feed concluída.")


if __name__ == "__main__":
    migrate()