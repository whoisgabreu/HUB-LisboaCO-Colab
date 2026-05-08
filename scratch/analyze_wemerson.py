import os
import sys
sys.path.append(os.getcwd())
from app import app
from database import Session
from sqlalchemy import text
from models import Investidor, MetricaMensal
import json

def analyze():
    with app.app_context():
        with Session() as db:
            inv = db.query(Investidor).filter(Investidor.email.ilike('%wemerson%')).first()
            if not inv:
                print("Wemerson not found")
                return
            
            print(f"Investidor: {inv.nome} ({inv.email})")
            
            metricas = db.query(MetricaMensal).filter(MetricaMensal.email_investidor == inv.email).order_by(MetricaMensal.ano, MetricaMensal.mes).all()
            for m in metricas:
                if m.ano != 2026 or m.mes not in (4, 5): continue
                print(f"\\nMês/Ano: {m.mes}/{m.ano}")
                print(f"Portfolio Total (MRR Carteira): {m.fixo_mrr_projeto_total}")
                print(f"MRR Entregue (novo_mrr): {m.fixo_mrr_entrega}")
                print(f"Churn Atual: {m.fixo_churn_atual}")
                print(f"MRR Atual Calculado (fixo_mrr_atual): {m.fixo_mrr_atual}")
                print(f"Remuneração Total (calc_remuneracao_total): {m.calc_remuneracao_total}")
                
                detalhes = m.detalhes.get('produtos', []) if m.detalhes else []
                churned_projects = [p for p in detalhes if p.get('churned')]
                if churned_projects:
                    print(f"Projetos Churned neste mês:")
                    for cp in churned_projects:
                        print(f"  - {cp['nome']} (ID: {cp['id']}, Fee full: {cp.get('fee')})")
                else:
                    print("Nenhum churn registrado neste mês.")

analyze()
