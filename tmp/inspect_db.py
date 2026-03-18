import os
from sqlalchemy import text
from database import Session

def inspect():
    with Session() as db:
        # Check columns
        res = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'plataforma_geral' 
            AND table_name = 'investidores_metricas_mensais_novo'
        """))
        columns = [r[0] for r in res]
        print(f"Columns in investidores_metricas_mensais_novo: {columns}")

        # Sample data
        res = db.execute(text("SELECT email_investidor, detalhes, historico_projetos FROM plataforma_geral.investidores_metricas_mensais_novo LIMIT 1"))
        row = res.fetchone()
        if row:
            print(f"Email: {row[0]}")
            print(f"Detalhes: {row[1]}")
            print(f"Historico Projetos: {row[2]}")
        else:
            print("No data found in table.")

if __name__ == "__main__":
    inspect()
