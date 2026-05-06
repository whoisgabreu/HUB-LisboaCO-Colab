"""
Script de correção em lote: atualiza meta de csat_checkin de 1 para 4
em TODAS as MetricaMensal.entregas_operacao do mês atual.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Session
from models import MetricaMensal
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime
import json

MES = datetime.now().month
ANO = datetime.now().year

def main():
    with Session() as db:
        metricas = db.query(MetricaMensal).filter_by(mes=MES, ano=ANO).all()
        print(f"Total de MetricaMensal para {MES}/{ANO}: {len(metricas)}")
        
        corrigidas = 0
        for m in metricas:
            entregas_op = m.entregas_operacao or []
            if not entregas_op:
                continue
            
            modified = False
            for entry in entregas_op:
                for ent in entry.get("entregas", []):
                    if ent.get("nome") == "csat_checkin" and ent.get("meta") != 4:
                        old = ent.get("meta")
                        ent["meta"] = 4
                        modified = True
                        print(f"  [{m.email_investidor}] proj={entry.get('projeto_id')} csat_checkin meta {old} -> 4")
            
            if modified:
                flag_modified(m, "entregas_operacao")
                corrigidas += 1
        
        if corrigidas > 0:
            db.commit()
            print(f"\n[OK] {corrigidas} MetricaMensal corrigida(s)")
        else:
            print("\nNenhuma correção necessária")

if __name__ == "__main__":
    main()
