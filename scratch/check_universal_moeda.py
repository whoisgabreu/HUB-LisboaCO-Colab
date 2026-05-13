"""Verifica TODA fonte de moeda para Universal Countertop."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

PID = 1071290432  # Universal Countertop

with engine.connect() as c:
    print("=== 1) projetos_ativos ===")
    r = c.execute(text(
        "SELECT pipefy_id, nome, fee, moeda FROM plataforma_geral.projetos_ativos WHERE pipefy_id = :p"
    ), {"p": PID}).fetchone()
    print(f"  {dict(r._mapping) if r else '(não está em projetos_ativos)'}")

with engine.connect() as c:
    print("\n=== 2) projetos ===")
    r = c.execute(text(
        "SELECT pipefy_id, nome, fee, moeda FROM plataforma_geral.projetos WHERE pipefy_id = :p"
    ), {"p": PID}).fetchone()
    print(f"  {dict(r._mapping) if r else '(não está em projetos)'}")

with engine.connect() as c:
    print("\n=== 3) projetos_inativos ===")
    try:
        r = c.execute(text(
            "SELECT pipefy_id, nome, fee, moeda FROM plataforma_geral.projetos_inativos WHERE pipefy_id = :p"
        ), {"p": PID}).fetchone()
        print(f"  {dict(r._mapping) if r else '(não está em projetos_inativos)'}")
    except Exception as e:
        print(f"  erro: {e}")

with engine.connect() as c:
    print("\n=== 4) investidores_projetos (vínculo) — TODAS as colunas ===")
    r = c.execute(text(
        "SELECT * FROM plataforma_geral.investidores_projetos WHERE pipefy_id_projeto = :p"
    ), {"p": PID}).fetchall()
    for row in r:
        print(f"  {dict(row._mapping)}")

with engine.connect() as c:
    print("\n=== 5) Quais colunas existem em investidores_projetos ===")
    r = c.execute(text(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema='plataforma_geral' AND table_name='investidores_projetos' "
        "ORDER BY ordinal_position"
    )).fetchall()
    for row in r:
        print(f"  {row[0]:<30} {row[1]}")
