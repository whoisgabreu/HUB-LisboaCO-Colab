
import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'plataforma_geral' AND table_name LIKE 'investidores_metricas%%'"
    res = conn.execute(text(sql))
    for row in res:
        print(row[0])
