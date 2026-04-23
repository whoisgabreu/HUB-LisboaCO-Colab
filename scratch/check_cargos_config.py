
import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    sql = "SELECT * FROM plataforma_geral.remuneracao_cargos WHERE fixo_cargo IN ('Designer', 'Gestor de Tráfego')"
    res = conn.execute(text(sql))
    cols = res.keys()
    for row in res:
        print(dict(zip(cols, row)))
        print("-" * 20)
