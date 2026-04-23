
import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    sql = "SELECT * FROM plataforma_geral.remuneracao_cargos WHERE fixo_cargo = 'Gestor de Tráfego' AND fixo_level = 'L3' AND fixo_senioridade = 'Pleno'"
    res = conn.execute(text(sql))
    cols = res.keys()
    for row in res:
        print(dict(zip(cols, row)))
