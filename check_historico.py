from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'plataforma_geral' AND table_name = 'investidores_metricas_mensais_novo'"))
    columns = [r[0] for r in res]
    print(f"Columns: {columns}")
    if 'historico_projetos' in columns:
        print("Column 'historico_projetos' FOUND!")
    else:
        print("Column 'historico_projetos' NOT FOUND.")
