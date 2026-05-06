import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    res = conn.execute(text("""
        SELECT column_name, data_type, generation_expression 
        FROM information_schema.columns 
        WHERE table_schema = 'plataforma_geral' 
        AND table_name = 'investidores_metricas_mensais_novo'
        AND is_generated = 'ALWAYS';
    """))
    for row in res:
        print(row)
