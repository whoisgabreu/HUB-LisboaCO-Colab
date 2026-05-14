import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

def check_status_values():
    with engine.connect() as conn:
        try:
            result = conn.execute(text("SELECT DISTINCT status FROM plataforma_geral.projetos;"))
            statuses = result.fetchall()
            print("Distinct statuses in plataforma_geral.projetos:")
            for s in statuses:
                print(f"- {s[0]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_status_values()
