
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("Columns in plataforma_geral.monthly_deliveries:")
    query = text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'plataforma_geral' AND table_name = 'monthly_deliveries'")
    result = conn.execute(query)
    for row in result:
        print(f"  - {row[0]}")
