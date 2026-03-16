import sys
import os
from datetime import date
from decimal import Decimal

# Add root to sys.path
sys.path.append(os.getcwd())

from services.projeto_participacao_service import ProjetoParticipacaoService

def test_calculation():
    print("--- Testando Cálculo Proporcional ---")
    
    # Exemplo: Projeto de 1000, trabalhado 15 dias em um mês de 31 dias
    # X = (15 * 1000) / 31 = 483,87
    fee = 1000
    data_inicio = date(2026, 3, 1)
    data_fim = date(2026, 3, 15)
    mes = 3
    ano = 2026
    
    val = ProjetoParticipacaoService.calcular_valor_proporcional(fee, data_inicio, data_fim, mes, ano)
    print(f"Março (31 dias), 15 dias, Fee 1000: Esperado ~483.87, Recebido: {val}")
    assert val == Decimal("483.87")

    # Mês completo
    data_fim_full = date(2026, 3, 31)
    val_full = ProjetoParticipacaoService.calcular_valor_proporcional(fee, data_inicio, data_fim_full, mes, ano)
    print(f"Março (31 dias), Mês completo, Fee 1000: Esperado 1000.00, Recebido: {val_full}")
    assert val_full == Decimal("1000.00")

    # Fevereiro (28 dias) 2026
    data_inicio_fev = date(2026, 2, 1)
    data_fim_fev = date(2026, 2, 14)
    val_fev = ProjetoParticipacaoService.calcular_valor_proporcional(fee, data_inicio_fev, data_fim_fev, 2, 2026)
    print(f"Fev (28 dias), 14 dias, Fee 1000: Esperado 500.00, Recebido: {val_fev}")
    assert val_fev == Decimal("500.00")

    # Fora do mês
    data_inicio_fora = date(2026, 4, 1)
    data_fim_fora = date(2026, 4, 15)
    val_fora = ProjetoParticipacaoService.calcular_valor_proporcional(fee, data_inicio_fora, data_fim_fora, 3, 2026)
    print(f"Fora do mês: Esperado 0.00, Recebido: {val_fora}")
    assert val_fora == Decimal("0.00")

    print("\nTodos os testes de cálculo passaram!")

if __name__ == "__main__":
    try:
        test_calculation()
    except Exception as e:
        print(f"ERRO nos testes: {e}")
        sys.exit(1)
