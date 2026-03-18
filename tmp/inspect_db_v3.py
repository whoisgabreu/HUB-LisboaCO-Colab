import os
import sys
import json

# Setup paths
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.append(root_dir)

from sqlalchemy import text
from database import Session

def inspect():
    with Session() as db:
        res = db.execute(text("SELECT email_investidor, mes, ano, historico_projetos FROM plataforma_geral.investidores_metricas_mensais_novo WHERE historico_projetos IS NOT NULL"))
        rows = res.fetchall()
        
        found_cientista = False
        total_records = 0
        
        for email, mes, ano, historico in rows:
            total_records += 1
            if historico:
                for item in historico:
                    if "cientista" in item:
                        found_cientista = True
                        print(f"FOUND cientista in {email} ({mes}/{ano}): {item['cientista']}")
                        print(f"Full item: {item}")
                        return # Just need to see one
        
        if not found_cientista:
            print(f"Checked {total_records} records, NO cientista key found anywhere.")

if __name__ == "__main__":
    inspect()
