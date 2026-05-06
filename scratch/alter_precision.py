import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # We will try to alter the columns to DECIMAL(15, 7)
    cols = [
        "calc_churn_real_percentual",
        "calc_delta_churn_percentual",
        "calc_delta_csp",
    ]
    
    for c in cols:
        try:
            print(f"Altering {c} to DECIMAL(15, 7)...")
            # In PostgreSQL, you can't alter a generated column's type directly if it depends on an expression
            # Wait, you can! Or we drop the generation and re-add it.
            # Actually, let's just alter the type.
            conn.execute(text(f"ALTER TABLE plataforma_geral.investidores_metricas_mensais_novo ALTER COLUMN {c} TYPE DECIMAL(15,7);"))
            print("Success")
        except Exception as e:
            print(f"Failed: {e}")
            
    conn.commit()
