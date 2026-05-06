import sys
import os
sys.path.append(os.getcwd())
from database import Session
from models import MetricaMensal
from app import _recalcular_mrr_por_entregas

def recalculate_operacao():
    with Session() as db:
        metricas = db.query(MetricaMensal).filter(
            MetricaMensal.ano == 2026,
            MetricaMensal.cargo.in_(["Account", "Gestor de Tráfego", "Cientista"])
        ).all()
        
        print(f"Encontrados {len(metricas)} registros de operação para 2026.")
        for m in metricas:
            # print(f"Antes {m.email_investidor} ({m.mes}/{m.ano}): {m.fixo_mrr_atual}")
            _recalcular_mrr_por_entregas(m)
        
        db.commit()
        print("Recálculo concluído com sucesso.")

if __name__ == "__main__":
    recalculate_operacao()
