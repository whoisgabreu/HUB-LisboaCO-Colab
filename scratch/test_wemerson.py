
import os
from database import Session
from models import Investidor, MetricaMensal, RemuneracaoCargo
from services.remuneracao import calcular_metricas_mensais
from decimal import Decimal

def test_wemerson_calculation():
    mes, ano = 4, 2026
    email = "wemerson.barbosa@v4company.com"
    
    print(f"--- Calculando métricas para {email} ({mes}/{ano}) ---")
    calcular_metricas_mensais(mes, ano)
    
    with Session() as db:
        m = db.query(MetricaMensal).filter_by(email_investidor=email, mes=mes, ano=ano).first()
        if m:
            print(f"MRR Total: {m.fixo_mrr_projeto_total}")
            print(f"Churn Atual: {m.fixo_churn_atual}")
            print(f"Detalhes: {m.detalhes}")
        else:
            print("Métrica não encontrada.")

if __name__ == "__main__":
    test_wemerson_calculation()
