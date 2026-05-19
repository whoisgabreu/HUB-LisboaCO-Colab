import sys
import os
sys.path.append(os.getcwd())

from database import Session
from models import Projeto, InvestidorProjeto, Investidor, MetricaMensal
from services.remuneracao import calcular_metricas_mensais
from decimal import Decimal

def test_usd_conversion():
    # ID do projeto USD conhecido
    pipefy_id = 1070792458 # Dr. Physio Therapy & Wellness
    
    with Session() as db:
        # 1. Verificar se o projeto está como USD na tabela unificada
        proj = db.query(Projeto).filter_by(pipefy_id=pipefy_id).first()
        if not proj:
            print(f"Projeto {pipefy_id} não encontrado na tabela unificada!")
            return
        
        print(f"Projeto: {proj.nome}")
        print(f"Moeda na tabela unificada: {proj.moeda}")
        
        # 2. Buscar investidores vinculados
        vinculos = db.query(InvestidorProjeto).filter_by(pipefy_id_projeto=pipefy_id, active=True).all()
        if not vinculos:
            print(f"Nenhum investidor ativo vinculado ao projeto {pipefy_id}")
            return
            
        for v in vinculos:
            print(f"\nInvestidor: {v.email_investidor}")
            print(f"Fee no vínculo (InvestidorProjeto): {v.fee_projeto}")
            print(f"Cientista: {v.cientista}")
            
            # Simular lógica do services/remuneracao.py
            moeda = proj.moeda
            fee_full = Decimal(str(v.fee_projeto or 0))
            if v.cientista:
                fee_full *= Decimal("1.5")
            
            if moeda == "USD":
                from services.currency import CurrencyService
                usd_rate = CurrencyService.get_usd_to_brl_rate()
                print(f"Taxa USD atual: {usd_rate}")
                fee_full_brl = fee_full * usd_rate
                print(f"Fee em BRL (com conversão): {fee_full_brl}")
            else:
                print(f"Fee em BRL (sem conversão): {fee_full}")

if __name__ == "__main__":
    test_usd_conversion()
