import sys
import os7JNHN
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    sql = "SELECT fixo_cargo, fixo_senioridade, fixo_level, calc_mrr_minima, fixo_mrr_teto FROM plataforma_geral.remuneracao_cargos WHERE fixo_cargo IN ('Account', 'Gestor de Tráfego')"
    res = conn.execute(text(sql)).fetchall()
    for r in res:
        print(f"Cargo: {r[0]}, Sen: {r[1]}, Level: {r[2]} | Min: {r[3]} | Teto: {r[4]}")
