import sys
import os
sys.path.append(os.getcwd())
from database import Session
from models import MetricaMensal, Investidor
from datetime import datetime as dt

with Session() as db:
    # Busca Pedro
    pedro = db.query(Investidor).filter(Investidor.nome.ilike("%Pedro Vitorino%")).first()
    if pedro:
        print(f"Investidor: {pedro.nome} ({pedro.email})")
        print(f"Cargo: {pedro.funcao}, Posicao: {pedro.posicao}")
        
        # Busca metricas
        metricas = db.query(MetricaMensal).filter_by(email_investidor=pedro.email).order_by(MetricaMensal.ano.desc(), MetricaMensal.mes.desc()).all()
        for m in metricas:
            print(f"\nMes: {m.mes}/{m.ano}")
            print(f"MRR Entrega: {m.fixo_mrr_entrega}")
            print(f"MRR Projeto Total: {m.fixo_mrr_projeto_total}")
            print(f"Remu Min: {m.fixo_remuneracao_minima}")
            print(f"Remu Max: {m.fixo_remuneracao_maxima}")
            print(f"Remu Total (Calc): {m.calc_remuneracao_total}")
            print(f"Entregas Op: {m.entregas_operacao}")
    else:
        print("Pedro nao encontrado")
