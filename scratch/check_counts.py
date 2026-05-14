import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

def check_count():
    with engine.connect() as conn:
        try:
            result = conn.execute(text("SELECT count(*) FROM plataforma_geral.projetos;"))
            count = result.scalar()
            print(f"Total rows in plataforma_geral.projetos: {count}")
            
            # Check activos, inativos, onetime
            result = conn.execute(text("SELECT count(*) FROM plataforma_geral.projetos_ativos;"))
            print(f"Total rows in plataforma_geral.projetos_ativos: {result.scalar()}")
            
            result = conn.execute(text("SELECT count(*) FROM plataforma_geral.projetos_inativos;"))
            print(f"Total rows in plataforma_geral.projetos_inativos: {result.scalar()}")
            
            result = conn.execute(text("SELECT count(*) FROM plataforma_geral.projetos_onetime;"))
            print(f"Total rows in plataforma_geral.projetos_onetime: {result.scalar()}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_count()
