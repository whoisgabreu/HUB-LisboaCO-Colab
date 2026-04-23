
import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    sql = "SELECT email_investidor, mes, ano FROM plataforma_geral.investidores_metricas_mensais_novo WHERE email_investidor = 'otavio.augusto@v4company.com'"
    res = conn.execute(text(sql))
    for row in res:
        print(row)
