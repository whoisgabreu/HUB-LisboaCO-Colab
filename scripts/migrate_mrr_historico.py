"""Migration: cria a tabela de histórico mensal de MRR por projeto.

Usage:
    python scripts/migrate_mrr_historico.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine, Base
from models import ProjetoMrrHistorico

SCHEMA = "plataforma_geral"


def migrate():
    print("Criando tabela de histórico de MRR...")
    Base.metadata.create_all(engine, tables=[ProjetoMrrHistorico.__table__])

    with engine.begin() as conn:
        conn.execute(text(
            f"CREATE INDEX IF NOT EXISTS ix_mrr_hist_ano_mes "
            f"ON {SCHEMA}.projeto_mrr_historico (ano, mes)"
        ))
        conn.execute(text(
            f"CREATE INDEX IF NOT EXISTS ix_mrr_hist_projeto "
            f"ON {SCHEMA}.projeto_mrr_historico (projeto_pipefy_id)"
        ))
    print("Tabela criada com sucesso.")


if __name__ == "__main__":
    migrate()
