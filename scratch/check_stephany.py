import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    sql = "SELECT fixo_remuneracao_fixa, fixo_remuneracao_minima FROM plataforma_geral.investidores_metricas_mensais_novo WHERE email_investidor = 'stephany.alves@v4company.com' AND mes=4"
    res = conn.execute(text(sql)).fetchone()
    print(res)
