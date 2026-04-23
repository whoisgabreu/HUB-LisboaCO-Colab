import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    sql = "SELECT DISTINCT cargo FROM plataforma_geral.investidores_metricas_mensais_novo"
    res = conn.execute(text(sql)).fetchall()
    print([r[0] for r in res])
