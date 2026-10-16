"""Migration: cria o schema painel_tech e aplica as migrações do Painel Gerencial TECH.

Usage:
    python scripts/migrate_painel_tech.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def migrate():
    from painel_tech import db as pdb

    print(f"Criando schema/tabelas em '{pdb.SCHEMA}'...")
    pdb.init_schema()
    novas = pdb.aplicar_migracoes()
    print("Migrações aplicadas:", novas or "nenhuma nova")
    print("Migração do Painel TECH concluída.")


if __name__ == "__main__":
    migrate()