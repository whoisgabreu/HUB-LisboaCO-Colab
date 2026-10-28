"""Seed pontual e idempotente: conta Meta da Somaxi Assessoria.

Importa manualmente a única conta Meta que existia apenas no texto do
contexto (id 26), sem parser automático. NÃO marca principal.

Dados revisados:
  projeto 1075727019 | meta_ads | 1417900892867332 | frente Assessoria

Usage:
    python scripts/seed_projetos_contas_somaxi.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

SCHEMA = "plataforma_geral"
PROJETO = 1075727019
PLATAFORMA = "meta_ads"
CONTA = "1417900892867332"
FRENTE = "Assessoria"
DESCRICAO = "Conta Meta — Somaxi Assessoria (importada do contexto id 26)"


def main():
    if not CONTA.isdigit():
        raise SystemExit("ID da conta inválido (use apenas dígitos).")

    with engine.begin() as conn:
        projeto = conn.execute(
            text(f"SELECT pipefy_id, nome FROM {SCHEMA}.projetos WHERE pipefy_id = :p"),
            {"p": PROJETO},
        ).mappings().first()
        if not projeto:
            raise SystemExit(f"Projeto {PROJETO} não encontrado.")

        inserido = conn.execute(text(f"""
            INSERT INTO {SCHEMA}.projetos_contas
                (projeto_pipefy_id, plataforma, conta_id, frente, descricao,
                 principal, ativo, updated_by)
            VALUES (:p, :plataforma, :conta, :frente, :descricao, FALSE, TRUE, 'migracao')
            ON CONFLICT (projeto_pipefy_id, plataforma, conta_id) DO NOTHING
        """), {
            "p": PROJETO,
            "plataforma": PLATAFORMA,
            "conta": CONTA,
            "frente": FRENTE,
            "descricao": DESCRICAO,
        }).rowcount

        meta = conn.execute(text(f"""
            SELECT count(*) FROM {SCHEMA}.projetos_contas
            WHERE projeto_pipefy_id = :p AND plataforma = 'meta_ads'
        """), {"p": PROJETO}).scalar()
        principal = conn.execute(text(f"""
            SELECT count(*) FROM {SCHEMA}.projetos_contas
            WHERE projeto_pipefy_id = :p AND plataforma = 'meta_ads' AND principal
        """), {"p": PROJETO}).scalar()

        print(f"Projeto: {projeto['nome']} ({PROJETO})")
        print(f"Seed: {'inserido' if inserido else 'já existia'}")
        print(f"Contas Meta no projeto: {meta} | principais: {principal}")


if __name__ == "__main__":
    main()
