import sys
sys.path.append('.')
from database import Session
from models import Investidor, MetricaMensal

with Session() as db:
    metricas = db.query(MetricaMensal).all()
    for m in metricas:
        if m.fixo_mrr_projeto_total and abs(float(m.fixo_mrr_projeto_total) - 106100.42) < 1.0:
            print(f"Found match: {m.email_investidor} (Mes: {m.mes}, Ano: {m.ano})")
            print(f"MRR Projeto Total (Carteira): {m.fixo_mrr_projeto_total}")
            print(f"MRR Entregue (Bruto): {m.fixo_mrr_entrega}")
            print(f"Churn Atual: {m.fixo_churn_atual}")
            print(f"MRR Atual (Entregue - Churn): {m.fixo_mrr_atual}")
