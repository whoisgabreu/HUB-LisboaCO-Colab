import os
import sys

# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Get the root directory (one level up from tmp)
root_dir = os.path.dirname(script_dir)
# Add root directory to sys.path
sys.path.append(root_dir)

from sqlalchemy import text
from database import Session

def inspect():
    with Session() as db:
        res = db.execute(text("SELECT email_investidor, mes, ano, detalhes, historico_projetos FROM plataforma_geral.investidores_metricas_mensais_novo WHERE historico_projetos IS NOT NULL LIMIT 2"))
        rows = res.fetchall()
        for row in rows:
            print("-" * 20)
            print(f"Email: {row[0]}, Mes/Ano: {row[1]}/{row[2]}")
            print(f"Historico Projetos: {row[4]}")
            if row[4] and len(row[4]) > 0:
                print(f"First Project Keys: {row[4][0].keys()}")

if __name__ == "__main__":
    inspect()
