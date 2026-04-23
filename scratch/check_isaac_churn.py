import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    sql = """
        SELECT pipefy_id_projeto, nome_projeto, fee_projeto, inactivated_at, cientista 
        FROM plataforma_geral.investidores_projetos 
        WHERE email_investidor = 'isaac.emanuel@v4company.com' 
          AND active = False 
          AND inactivated_at IS NOT NULL
    """
    res = conn.execute(text(sql)).fetchall()
    print("Isaac's churned projects:")
    for r in res:
        print(f"ID: {r[0]} | Nome: {r[1]} | Fee: {r[2]} | Inactivated: {r[3]} | Cientista: {r[4]}")
