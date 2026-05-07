import sys
sys.path.append('.')
from database import Session
from models import MetricaMensal

with Session() as db:
    metrica = db.query(MetricaMensal).filter(MetricaMensal.email_investidor.like('%wemerson%'), MetricaMensal.mes == 4, MetricaMensal.ano == 2026).first()
    if metrica:
        print("Wemerson (Mes 4):")
        print(f"MRR Projeto Total (Carteira): {metrica.fixo_mrr_projeto_total}")
        print(f"MRR Entregue (Bruto): {metrica.fixo_mrr_entrega}")
        print(f"Churn Atual: {metrica.fixo_churn_atual}")
        print(f"MRR Atual (Entregue - Churn): {metrica.fixo_mrr_atual}")
    else:
        print("Metrica não encontrada para Wemerson")
