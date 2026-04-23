
import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    sql = """
    SELECT column_name, generation_expression 
    FROM information_schema.columns 
    WHERE table_schema = 'plataforma_geral' 
      AND table_name = 'investidores_metricas_mensais_novo' 
      AND generation_expression IS NOT NULL
    """
    res = conn.execute(text(sql))
    for row in res:
        print(f"Column: {row[0]}")
        print(f"Expression: {row[1]}")
        print("-" * 20)
