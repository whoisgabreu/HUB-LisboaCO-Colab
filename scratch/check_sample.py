import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

def check_sample_data():
    with engine.connect() as conn:
        try:
            result = conn.execute(text("SELECT * FROM plataforma_geral.projetos LIMIT 5;"))
            rows = result.fetchall()
            print(f"Sample data from plataforma_geral.projetos ({len(rows)} rows):")
            for row in rows:
                print(row)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_sample_data()
