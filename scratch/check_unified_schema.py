import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

def check_unified_table():
    with engine.connect() as conn:
        try:
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'plataforma_geral' AND table_name = 'projetos'
                ORDER BY ordinal_position;
            """))
            columns = result.fetchall()
            if not columns:
                print("Table plataforma_geral.projetos not found or has no columns.")
            else:
                print("Columns in plataforma_geral.projetos:")
                for col in columns:
                    print(f"- {col[0]}: {col[1]}")
            
            # Also check for data to see how statuses are represented
            result = conn.execute(text("SELECT DISTINCT phase_name FROM plataforma_geral.projetos LIMIT 10;"))
            phases = result.fetchall()
            print("\nDistinct phases (sample):")
            for p in phases:
                print(f"- {p[0]}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_unified_table()
