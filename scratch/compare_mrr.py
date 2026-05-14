import sys
import os
sys.path.append(os.getcwd())

from database import Session
from models import ProjetoAtivo, Projeto
from services.currency import CurrencyService
from decimal import Decimal

def compare_mrr_detailed():
    with Session() as db:
        usd_rate = float(CurrencyService.get_usd_to_brl_rate())
        
        # 1. Dados Legado
        ativos_legado = db.query(ProjetoAtivo).all()
        legado_map = {p.pipefy_id: p for p in ativos_legado}
        
        # 2. Dados Unificados
        ativos_unificado = db.query(Projeto).filter_by(status='Ativo').all()
        unificado_map = {p.pipefy_id: p for p in ativos_unificado}
        
        mrr_legado = 0
        for p in ativos_legado:
            fee = float(p.fee or 0)
            moeda = str(p.moeda).strip().upper() if p.moeda else "BRL"
            mrr_legado += fee * usd_rate if moeda == "USD" else fee
            
        mrr_unificado = 0
        for p in ativos_unificado:
            fee = float(p.fee or 0)
            moeda = str(p.moeda).strip().upper() if p.moeda else "BRL"
            mrr_unificado += fee * usd_rate if moeda == "USD" else fee
            
        print(f"MRR Legado: {mrr_legado:,.2f}")
        print(f"MRR Unificado: {mrr_unificado:,.2f}")
        print(f"Diferença: {mrr_legado - mrr_unificado:,.2f}")

        print("\n--- Projetos com Diferença de Fee ou Moeda ---")
        common_ids = set(legado_map.keys()) & set(unificado_map.keys())
        for pid in common_ids:
            p_leg = legado_map[pid]
            p_uni = unificado_map[pid]
            
            f_leg = float(p_leg.fee or 0)
            f_uni = float(p_uni.fee or 0)
            m_leg = str(p_leg.moeda).strip().upper() if p_leg.moeda else "BRL"
            m_uni = str(p_uni.moeda).strip().upper() if p_uni.moeda else "BRL"
            
            if f_leg != f_uni or m_leg != m_uni:
                print(f"ID: {pid} | Nome: {p_leg.nome}")
                print(f"  Legado: Fee={f_leg}, Moeda={m_leg}")
                print(f"  Unificado: Fee={f_uni}, Moeda={m_uni}")

if __name__ == "__main__":
    compare_mrr_detailed()
