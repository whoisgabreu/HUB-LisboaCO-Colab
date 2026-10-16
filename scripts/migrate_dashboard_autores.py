"""Migration: cria a tabela analise_grupos_cliente.autores e importa
o conteudo de equipe.json / clientes.json (se existirem).

Usage:
    python scripts/migrate_dashboard_autores.py
"""
import os
import re
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from dashboard_grupos.db import DB_URL, SCHEMA

TABLE = "autores"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _norm(nome):
    if not nome:
        return ""
    return re.sub(r"\s+", " ", str(nome).strip()).lower()


def migrate():
    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            print(f'Criando tabela "{SCHEMA}"."{TABLE}"...')
            cur.execute(
                f'CREATE TABLE IF NOT EXISTS "{SCHEMA}"."{TABLE}" ('
                "id SERIAL PRIMARY KEY, "
                "nome TEXT NOT NULL, "
                "nome_norm TEXT NOT NULL UNIQUE, "
                "papel TEXT NOT NULL, "
                "tipo TEXT NOT NULL CHECK (tipo IN ('equipe','cliente')), "
                "atualizado_em TIMESTAMP DEFAULT now())"
            )
            conn.commit()

            total = {"equipe": 0, "cliente": 0}
            for fname, tipo in (("equipe.json", "equipe"), ("clientes.json", "cliente")):
                path = os.path.join(BASE, fname)
                if not os.path.exists(path):
                    print(f"{fname}: não encontrado (ignorado).")
                    continue
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                for nome, papel in (data or {}).items():
                    nn = _norm(nome)
                    if not nn:
                        continue
                    cur.execute(
                        f'INSERT INTO "{SCHEMA}"."{TABLE}" (nome, nome_norm, papel, tipo, atualizado_em) '
                        "VALUES (%s, %s, %s, %s, now()) "
                        "ON CONFLICT (nome_norm) DO UPDATE SET nome=EXCLUDED.nome, "
                        "papel=EXCLUDED.papel, tipo=EXCLUDED.tipo, atualizado_em=now()",
                        (str(nome).strip(), nn, papel, tipo),
                    )
                    total[tipo] += 1
                print(f"{fname}: {len(data or {})} registro(s) importado(s).")
            conn.commit()

            cur.execute(f'SELECT tipo, count(*) FROM "{SCHEMA}"."{TABLE}" GROUP BY tipo')
            print("Total na tabela:", dict(cur.fetchall()))
    finally:
        conn.close()
    print("Migração concluída.")


if __name__ == "__main__":
    migrate()