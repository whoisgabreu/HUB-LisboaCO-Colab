from database import engine
from sqlalchemy import text

def check_columns():
    with engine.connect() as conn:
        print("\n--- COLUMNS of investidores_projetos ---")
        q = text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'plataforma_geral' 
            AND table_name = 'investidores_projetos'
        """)
        res = conn.execute(q).fetchall()
        for r in res:
            print(f"Column: {r[0]} | Type: {r[1]}")

if __name__ == "__main__":
    check_columns()
