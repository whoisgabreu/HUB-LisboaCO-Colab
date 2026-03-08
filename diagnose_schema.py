
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("--- Diagnostic: plataforma_geral.monthly_deliveries ---")
    try:
        query = text("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'plataforma_geral' AND table_name = 'monthly_deliveries'")
        result = conn.execute(query)
        columns = {row[0]: row[1] for row in result}
        if not columns:
            print("Table not found!")
        for col, dtype in columns.items():
            print(f"  - {col} ({dtype})")
    except Exception as e:
        print(f"Error checking table: {e}")
