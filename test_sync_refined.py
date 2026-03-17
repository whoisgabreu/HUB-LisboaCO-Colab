import sys
import os
from datetime import date
from decimal import Decimal

# Add root to sys.path
sys.path.append(os.getcwd())

from services.projeto_participacao_service import ProjetoParticipacaoService

def test_refined_sync_logic():
    print("--- Testando Lógica de Sincronização Refinada ---")
    
    # 1. Testar Regra de Data Inicial (Março 2026)
    # Se mes=3 e ano=2026, data_inicio deve ser 2026-03-01 mesmo se o vínculo for anterior
    fee = 1000
    v_inicio_antigo = date(2025, 12, 1)
    mes = 3
    ano = 2026
    
    # Simulação da regra dentro do sincronizar_remuneracao:
    # data_inicio_padrao = date(2026, 3, 1) if (mes == 3 and ano == 2026) else date(ano, mes, 1)
    # v_inicio = max(v_inicio_antigo, date(2026, 3, 1))
    
    v_inicio_calc = max(v_inicio_antigo, date(2026, 3, 1))
    val = ProjetoParticipacaoService.calcular_valor_proporcional(fee, v_inicio_calc, None, mes, ano)
    print(f"Março 2026, Vínculo Antigo (2025): Esperado 1000.00 (Início em 2026-03-01), Recebido: {val}")
    assert val == Decimal("1000.00")

    # 2. Testar Churn no Mês Corrente
    # Inativado em 15/03/2026
    v_fim_churn = date(2026, 3, 15)
    val_churn = ProjetoParticipacaoService.calcular_valor_proporcional(fee, v_inicio_calc, v_fim_churn, mes, ano)
    print(f"Março 2026, Churn em 15/03: Esperado 483.87, Recebido: {val_churn}")
    assert val_churn == Decimal("483.87")

    # 3. Testar Meses Normais (Abril 2026)
    mes_abr = 4
    v_inicio_abr = date(2026, 4, 10) # Entrou no meio do mês
    val_abr = ProjetoParticipacaoService.calcular_valor_proporcional(fee, v_inicio_abr, None, mes_abr, 2026)
    # Abril tem 30 dias. Do dia 10 ao 30 são 21 dias.
    # X = (21 * 1000) / 30 = 700.00
    print(f"Abril 2026, Início em 10/04: Esperado 700.00, Recebido: {val_abr}")
    assert val_abr == Decimal("700.00")

    print("\nTodos os testes de lógica refinada passaram!")

if __name__ == "__main__":
    test_refined_sync_logic()
