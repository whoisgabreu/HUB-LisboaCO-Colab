"""Migration: canal Desabafo 100% anônimo.

Cria a tabela de posts (sem qualquer identificação do autor) e registra a tela
`desabafo` no catálogo de acessos, concedendo moderação (editar) a cargos e
posições com a capacidade gestao_ampla.

Usage:
    python scripts/migrate_desabafo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

SCHEMA = "plataforma_geral"


def migrate():
    with engine.begin() as conn:
        print("Criando tabela desabafo_posts...")
        conn.execute(text(
            f'CREATE TABLE IF NOT EXISTS "{SCHEMA}".desabafo_posts ('
            "id SERIAL PRIMARY KEY, "
            "conteudo TEXT NOT NULL, "
            "categoria TEXT, "
            "criado_dia DATE NOT NULL DEFAULT CURRENT_DATE, "
            "oculto BOOLEAN NOT NULL DEFAULT FALSE, "
            "deletado BOOLEAN NOT NULL DEFAULT FALSE)"
        ))
        conn.execute(text(
            f'CREATE INDEX IF NOT EXISTS desabafo_posts_ordem_idx '
            f'ON "{SCHEMA}".desabafo_posts (deletado, oculto, id DESC)'
        ))

        print("Registrando a tela 'desabafo'...")
        conn.execute(text(
            f'INSERT INTO "{SCHEMA}".v2_telas (codigo, nome, grupo, ordem, acesso_padrao, ativo) '
            "VALUES ('desabafo', 'Desabafo', 'Comunidade', 5, 'ver', TRUE) "
            "ON CONFLICT (codigo) DO UPDATE SET nome=EXCLUDED.nome, grupo=EXCLUDED.grupo, "
            "ordem=EXCLUDED.ordem, acesso_padrao=EXCLUDED.acesso_padrao, ativo=TRUE"
        ))

        print("Concedendo moderação (editar) a cargos/posições com gestao_ampla...")
        for tabela, coluna, cap in (
            ("v2_cargo_telas", "cargo", "v2_cargo_capacidades"),
            ("v2_posicao_telas", "posicao", "v2_posicao_capacidades"),
        ):
            orig = "cargo" if coluna == "cargo" else "posicao"
            conn.execute(text(
                f'INSERT INTO "{SCHEMA}"."{tabela}" ("{coluna}", tela, nivel) '
                f'SELECT "{orig}", \'desabafo\', \'editar\' FROM "{SCHEMA}"."{cap}" '
                "WHERE capacidade = 'gestao_ampla' "
                f'ON CONFLICT ("{coluna}", tela) DO UPDATE SET nivel = \'editar\''
            ))

    print("Migração do Desabafo concluída.")


if __name__ == "__main__":
    migrate()