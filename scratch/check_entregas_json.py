import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    sql = "SELECT entregas_criativos FROM plataforma_geral.investidores_metricas_mensais_novo WHERE entregas_criativos IS NOT NULL LIMIT 1"
    res = conn.execute(text(sql)).fetchone()
    print(res[0] if res else 'None')
