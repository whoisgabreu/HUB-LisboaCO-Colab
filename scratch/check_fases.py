import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

def check_fases():
    with engine.connect() as conn:
        try:
            print("Fases in projetos_ativos:")
            result = conn.execute(text("SELECT DISTINCT fase_do_pipefy FROM plataforma_geral.projetos_ativos;"))
            for r in result: print(f"- {r[0]}")
            
            print("\nFases in projetos_inativos:")
            result = conn.execute(text("SELECT DISTINCT fase_do_pipefy FROM plataforma_geral.projetos_inativos;"))
            for r in result: print(f"- {r[0]}")
            
            print("\nFases in projetos_onetime:")
            result = conn.execute(text("SELECT DISTINCT fase_do_pipefy FROM plataforma_geral.projetos_onetime;"))
            for r in result: print(f"- {r[0]}")
            
            print("\nFases in projetos (unified):")
            result = conn.execute(text("SELECT DISTINCT fase_do_pipefy FROM plataforma_geral.projetos LIMIT 20;"))
            for r in result: print(f"- {r[0]}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_fases()
