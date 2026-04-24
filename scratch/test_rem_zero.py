import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text
from decimal import Decimal

with engine.connect() as conn:
    # Simula a formula SQL
    fixo_remuneracao_fixa = Decimal("3250.00")
    fixo_mrr_atual = Decimal("0.00")
    fixo_csp_esperado = Decimal("0.0290179")
    fixo_churn_maximo_percentual = Decimal("0.0650000")
    fixo_churn_atual = Decimal("0.00")

    sql = """
    SELECT (
        :fixo + 
        ((:csp - (:fixo / NULLIF(:mrr, 0))) * :mrr) + 
        (((:churn_max - (:churn / NULLIF(:mrr, 0))) * :mrr) * :csp)
    ) as rem_calc
    """
    res = conn.execute(text(sql), {
        "fixo": fixo_remuneracao_fixa,
        "mrr": fixo_mrr_atual,
        "csp": fixo_csp_esperado,
        "churn_max": fixo_churn_maximo_percentual,
        "churn": fixo_churn_atual
    }).scalar()
    print("SQL Calc Rem:", res)
