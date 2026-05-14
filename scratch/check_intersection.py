import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

def check_intersection():
    with engine.connect() as conn:
        try:
            print("Checking pipefy_id from projetos_ativos in projetos:")
            result = conn.execute(text("""
                SELECT p.pipefy_id, p.status, p.fase_do_pipefy 
                FROM plataforma_geral.projetos p
                JOIN plataforma_geral.projetos_ativos a ON p.pipefy_id = a.pipefy_id
                LIMIT 10;
            """))
            rows = result.fetchall()
            for r in rows:
                print(f"PipefyID: {r[0]}, Status in unified: {r[1]}, Fase: {r[2]}")
                
            print("\nChecking counts:")
            result = conn.execute(text("""
                SELECT count(*) 
                FROM plataforma_geral.projetos p
                JOIN plataforma_geral.projetos_ativos a ON p.pipefy_id = a.pipefy_id;
            """))
            print(f"Ativos found in unified: {result.scalar()}")
            
            result = conn.execute(text("""
                SELECT count(*) 
                FROM plataforma_geral.projetos p
                JOIN plataforma_geral.projetos_inativos i ON p.pipefy_id = i.pipefy_id;
            """))
            print(f"Inativos found in unified: {result.scalar()}")
            
            result = conn.execute(text("""
                SELECT count(*) 
                FROM plataforma_geral.projetos p
                JOIN plataforma_geral.projetos_onetime o ON p.pipefy_id = o.pipefy_id;
            """))
            print(f"Onetime found in unified: {result.scalar()}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_intersection()
