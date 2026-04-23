import sys
import os
sys.path.append(os.getcwd())
from database import Session
from services.remuneracao import calcular_metricas_mensais
from models import MetricaMensal, Investidor

mes = 4
ano = 2026

print(f"Calculando metricas para {mes}/{ano}...")
calcular_metricas_mensais(mes, ano)

with Session() as db:
    pedro = db.query(Investidor).filter(Investidor.nome.ilike("%Pedro Vitorino%")).first()
    m = db.query(MetricaMensal).filter_by(email_investidor=pedro.email, mes=mes, ano=ano).first()
    if m:
        print(f"\nPos-Calculo Pedro Vitorino:")
        print(f"MRR Entrega: {m.fixo_mrr_entrega}")
        print(f"MRR Projeto Total: {m.fixo_mrr_projeto_total}")
        print(f"Remu Min: {m.fixo_remuneracao_minima}")
        print(f"Remu Max: {m.fixo_remuneracao_maxima}")
        print(f"Entregas Op: {m.entregas_operacao}")
