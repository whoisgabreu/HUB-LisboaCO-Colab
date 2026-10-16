"""Migration: cria a tabela definitiva de tokens do Google Agenda por usuário
e migra/dropa a tabela temporária google_oauth_tmp (do teste).

Usage:
    python scripts/migrate_google_agenda.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

SCHEMA = "plataforma_geral"
TABELA = f"{SCHEMA}.usuario_google_token"
TMP = f"{SCHEMA}.google_oauth_tmp"


def migrate():
    print("Criando tabela usuario_google_token...")
    with engine.begin() as conn:
        conn.execute(text(
            f"CREATE TABLE IF NOT EXISTS {TABELA} ("
            "email TEXT PRIMARY KEY, "
            "refresh_token TEXT, "
            "scope TEXT, "
            "atualizado_em TIMESTAMP DEFAULT now())"
        ))

        existe_tmp = conn.execute(text(
            "SELECT to_regclass(:t)"
        ), {"t": f"{SCHEMA}.google_oauth_tmp"}).scalar()

        if existe_tmp:
            print("Migrando dados de google_oauth_tmp...")
            conn.execute(text(
                f"INSERT INTO {TABELA} (email, refresh_token, scope, atualizado_em) "
                f"SELECT email, refresh_token, scope, criado_em FROM {TMP} "
                "ON CONFLICT (email) DO UPDATE SET "
                "refresh_token=EXCLUDED.refresh_token, scope=EXCLUDED.scope, atualizado_em=EXCLUDED.atualizado_em"
            ))
            print("Dropping google_oauth_tmp...")
            conn.execute(text(f"DROP TABLE IF EXISTS {TMP}"))
        else:
            print("google_oauth_tmp não existe (nada a migrar).")

    print("Migração concluída.")


if __name__ == "__main__":
    migrate()