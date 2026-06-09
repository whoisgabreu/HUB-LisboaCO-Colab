"""Migration: Create automacoes and automacoes_log tables.

Usage:
    python scripts/migrate_automacoes.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base
from models import Automacao, AutomacaoLog

def migrate():
    """Create the automation tables if they don't exist."""
    print("Criando tabelas de automações...")
    Base.metadata.create_all(engine, tables=[
        Automacao.__table__,
        AutomacaoLog.__table__,
    ])
    print("Tabelas criadas com sucesso.")

if __name__ == "__main__":
    migrate()
