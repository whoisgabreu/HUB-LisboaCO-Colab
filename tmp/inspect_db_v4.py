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
        
        counts = {"True": 0, "False": 0, "Missing": 0}
        
        for email, mes, ano, historico in rows:
            if historico:
                for item in historico:
                    val = item.get("cientista", "Missing")
                    if val == True: counts["True"] += 1
                    elif val == False: counts["False"] += 1
                    else: counts["Missing"] += 1
        
        print(f"Stats: {counts}")
        
        # Show one of each if possible
        found_t = False
        found_f = False
        for email, mes, ano, historico in rows:
            if historico:
                for item in historico:
                    if item.get("cientista") == True and not found_t:
                        print(f"Scientist (True): {email} -> {item}")
                        found_t = True
                    if item.get("cientista") == False and not found_f:
                        print(f"Scientist (False): {email} -> {item}")
                        found_f = True
            if found_t and found_f: break

if __name__ == "__main__":
    inspect()
