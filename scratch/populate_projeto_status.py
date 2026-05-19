import sys
import os
sys.path.append(os.getcwd())
from database import Session, engine
from sqlalchemy import text

def populate_status():
    with Session() as session:
        try:
            print("Populating status 'Inativo'...")
            session.execute(text("""
                UPDATE plataforma_geral.projetos p
                SET status = 'Inativo',
                    fee = i.fee,
                    moeda = i.moeda
                FROM plataforma_geral.projetos_inativos i
                WHERE p.pipefy_id = i.pipefy_id;
            """))
            
            print("Populating status 'Onetime'...")
            session.execute(text("""
                UPDATE plataforma_geral.projetos p
                SET status = 'Onetime',
                    fee = o.fee,
                    moeda = o.moeda
                FROM plataforma_geral.projetos_onetime o
                WHERE p.pipefy_id = o.pipefy_id;
            """))

            print("Populating status 'Ativo'...")
            session.execute(text("""
                UPDATE plataforma_geral.projetos p
                SET status = 'Ativo',
                    fee = a.fee,
                    moeda = a.moeda
                FROM plataforma_geral.projetos_ativos a
                WHERE p.pipefy_id = a.pipefy_id;
            """))
            
            session.commit()
            print("Migration of status column completed successfully.")
            
            # Check counts
            result = session.execute(text("SELECT status, count(*) FROM plataforma_geral.projetos GROUP BY status;"))
            print("\nFinal status counts in plataforma_geral.projetos:")
            for r in result:
                print(f"- {r[0]}: {r[1]}")
                
        except Exception as e:
            session.rollback()
            print(f"Error during migration: {e}")

if __name__ == "__main__":
    populate_status()
