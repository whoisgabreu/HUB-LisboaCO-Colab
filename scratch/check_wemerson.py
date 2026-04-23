import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    sql = "SELECT entregas_criativos FROM plataforma_geral.investidores_metricas_mensais_novo WHERE email_investidor = 'wemerson.barbosa@v4company.com' AND mes = 4 AND ano = 2026"
    res = conn.execute(text(sql)).fetchone()
    print(res[0] if res else 'None')
