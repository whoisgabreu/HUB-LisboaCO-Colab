
import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    sql = "SELECT * FROM plataforma_geral.investidores_metricas_mensais_novo WHERE mes = 4 AND ano = 2026 AND (email_investidor LIKE 'wemerson%%' OR email_investidor LIKE 'otavio%%')"
    res = conn.execute(text(sql))
    cols = res.keys()
    for row in res:
        print(dict(zip(cols, row)))
        print("-" * 20)
