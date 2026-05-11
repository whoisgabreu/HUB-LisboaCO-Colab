from decimal import Decimal
from datetime import date, timedelta

class MockService:
    @staticmethod
    def get_total_days_in_month(mes, ano):
        import calendar
        return calendar.monthrange(ano, mes)[1]

    @staticmethod
    def calcular_valor_proporcional(fee, data_inicio, data_fim, mes, ano):
        total_dias_mes = MockService.get_total_days_in_month(mes, ano)
        inicio_mes = date(ano, mes, 1)
        fim_mes = date(ano, mes, total_dias_mes)
        data_fim_calc_val = data_fim if data_fim else fim_mes
        data_inicio_calc = max(data_inicio, inicio_mes)
        data_fim_calc = min(data_fim_calc_val, fim_mes)
        if data_inicio_calc > data_fim_calc:
            return Decimal("0.00")
        dias_trabalhados = (data_fim_calc - data_inicio_calc).days + 1
        return (Decimal(dias_trabalhados) * Decimal(str(fee))) / Decimal(total_dias_mes)

def test_logic(fee_projeto, v_inicio, v_fim, c_entrada, c_saida, mes, ano):
    import calendar
    total_dias_mes = calendar.monthrange(ano, mes)[1]
    fim_mes = date(ano, mes, total_dias_mes)
    
    fee_base = Decimal(str(fee_projeto))
    
    # Logic from the service
    real_v_fim = v_fim if v_fim else fim_mes
    actual_c_saida = c_saida if c_saida else real_v_fim
    
    s_start = max(v_inicio, c_entrada) if c_entrada else None
    s_end = min(real_v_fim, actual_c_saida) if actual_c_saida else None
    
    if s_start and s_end and s_start <= s_end:
        valor_cientista = MockService.calcular_valor_proporcional(
            fee_base * Decimal("1.5"), s_start, s_end, mes, ano
        )
        
        valor_investidor_puro = Decimal("0.00")
        if v_inicio < s_start:
            valor_investidor_puro += MockService.calcular_valor_proporcional(
                fee_base, v_inicio, s_start - timedelta(days=1), mes, ano
            )
        if real_v_fim > s_end:
            valor_investidor_puro += MockService.calcular_valor_proporcional(
                fee_base, s_end + timedelta(days=1), real_v_fim, mes, ano
            )
        
        v_valor_prop = valor_cientista + valor_investidor_puro
    else:
        v_valor_prop = MockService.calcular_valor_proporcional(
            fee_base, v_inicio, v_fim, mes, ano
        )
        
    return v_valor_prop.quantize(Decimal("0.01"))

# Scenario: Fee 1000, Month 30 days.
# Project: 1 to 30.
# Scientist: 11 to 20.
# Expected: (20 * 1000 + 10 * 1500) / 30 = (20000 + 15000) / 30 = 35000 / 30 = 1166.67
print(f"Scenario 1: {test_logic(1000, date(2026, 5, 1), None, date(2026, 5, 11), date(2026, 5, 20), 5, 2026)}")

# Scenario 2: Null exit date.
# Project: 1 to 30.
# Scientist: 11 to (end).
# Expected: (10 * 1000 + 20 * 1500) / 30 = (10000 + 30000) / 30 = 40000 / 30 = 1333.33
print(f"Scenario 2: {test_logic(1000, date(2026, 5, 1), None, date(2026, 5, 11), None, 5, 2026)}")

# Scenario 3: Scientist starts before project (should be capped at project start).
# Project: 11 to 30.
# Scientist: 1 to (end).
# Expected: (20 days * 1500) / 31 = 30000 / 31 = 967.74 (May has 31 days)
print(f"Scenario 3: {test_logic(1000, date(2026, 5, 11), None, date(2026, 5, 1), None, 5, 2026)}")
