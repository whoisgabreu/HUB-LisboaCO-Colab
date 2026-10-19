"""Reparo dos padrões de acesso (safety pass).

- Rebaixa 'projetos' de editar -> ver para cargos/posições que NÃO são gestão
  (operacao_account / operacao_gt sem gestao_ampla / gestao_squad).
- Garante 'remuneracao: ver' para quem tem gestao_squad (Coordenador).
- Garante 'cs_cx: ver' para quem tem operacao_account (Account).
- Garante 'desabafo: editar' para quem tem gestao_ampla.
Idempotente. NÃO altera o cargo Desenvolvedor (mantém acesso amplo).

Usage:
    python scripts/repair_acessos_defaults.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

S = "plataforma_geral"


def _reparar(conn, tabela, coluna, capacidades):
    cap = capacidades

    # 1) projetos: editar -> ver (apenas não-gestão)
    r1 = conn.execute(text(
        f'UPDATE "{S}"."{tabela}" ct SET nivel = \'ver\' '
        "WHERE ct.tela = 'projetos' AND ct.nivel = 'editar' "
        f'AND EXISTS (SELECT 1 FROM "{S}"."{cap}" cc WHERE cc."{coluna}" = ct."{coluna}" '
        "AND cc.capacidade IN ('operacao_account','operacao_gt')) "
        f'AND NOT EXISTS (SELECT 1 FROM "{S}"."{cap}" cc WHERE cc."{coluna}" = ct."{coluna}" '
        "AND cc.capacidade IN ('gestao_ampla','gestao_squad'))"
    )).rowcount

    # 2) remuneracao: ver para gestao_squad
    r2 = conn.execute(text(
        f'INSERT INTO "{S}"."{tabela}" ("{coluna}", tela, nivel) '
        f'SELECT DISTINCT "{coluna}", \'remuneracao\', \'ver\' FROM "{S}"."{cap}" '
        "WHERE capacidade = 'gestao_squad' "
        f'ON CONFLICT ("{coluna}", tela) DO NOTHING'
    )).rowcount

    # 3) cs_cx: ver para operacao_account
    r3 = conn.execute(text(
        f'INSERT INTO "{S}"."{tabela}" ("{coluna}", tela, nivel) '
        f'SELECT DISTINCT "{coluna}", \'cs_cx\', \'ver\' FROM "{S}"."{cap}" '
        "WHERE capacidade = 'operacao_account' "
        f'ON CONFLICT ("{coluna}", tela) DO NOTHING'
    )).rowcount

    # 4) desabafo: editar para gestao_ampla
    r4 = conn.execute(text(
        f'INSERT INTO "{S}"."{tabela}" ("{coluna}", tela, nivel) '
        f'SELECT DISTINCT "{coluna}", \'desabafo\', \'editar\' FROM "{S}"."{cap}" '
        "WHERE capacidade = 'gestao_ampla' "
        f'ON CONFLICT ("{coluna}", tela) DO UPDATE SET nivel = \'editar\''
    )).rowcount

    return {"projetos->ver": r1, "remuneracao": r2, "cs_cx": r3, "desabafo": r4}


def migrate():
    with engine.begin() as conn:
        print("Cargos:", _reparar(conn, "v2_cargo_telas", "cargo", "v2_cargo_capacidades"))
        print("Posições:", _reparar(conn, "v2_posicao_telas", "posicao", "v2_posicao_capacidades"))
    print("Reparo concluído.")


if __name__ == "__main__":
    migrate()