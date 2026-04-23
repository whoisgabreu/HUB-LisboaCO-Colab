"""
Diagnóstico completo do sistema de remuneração.
Lê TUDO do banco de dados sem alterar nada.
"""
import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text
from decimal import Decimal

with engine.connect() as conn:
    print("=" * 80)
    print("1. COLUNAS CALCULADAS (GENERATED) DA TABELA investidores_metricas_mensais_novo")
    print("=" * 80)
    sql = """
    SELECT column_name, data_type, generation_expression 
    FROM information_schema.columns 
    WHERE table_schema = 'plataforma_geral' 
      AND table_name = 'investidores_metricas_mensais_novo'
    ORDER BY ordinal_position
    """
    res = conn.execute(text(sql))
    for row in res:
        gen = row[2] or ""
        prefix = " [GENERATED]" if gen else ""
        print(f"  {row[0]} ({row[1]}){prefix}")
        if gen:
            print(f"    Formula: {gen}")
    
    print("\n" + "=" * 80)
    print("2. DADOS DO OTÁVIO (otavio.augusto@v4company.com) - Abril 2026")
    print("=" * 80)
    sql = """SELECT 
        email_investidor, cargo, senioridade, level,
        fixo_remuneracao_fixa, fixo_csp_esperado, fixo_churn_maximo_percentual,
        fixo_mrr_minimo, fixo_mrr_esperado, fixo_mrr_teto,
        fixo_mrr_atual, fixo_mrr_entrega, fixo_mrr_projeto_total,
        fixo_churn_atual, fixo_churn_maximo_valor,
        fixo_remuneracao_minima, fixo_remuneracao_maxima,
        calc_churn_real_percentual, calc_delta_churn_percentual, calc_delta_churn_valor,
        calc_variavel_churn, calc_delta_csp, calc_variavel_csp,
        calc_variavel_total, calc_remuneracao_total
    FROM plataforma_geral.investidores_metricas_mensais_novo 
    WHERE email_investidor = 'otavio.augusto@v4company.com' AND mes = 4 AND ano = 2026"""
    res = conn.execute(text(sql))
    row = res.mappings().first()
    if row:
        for k, v in row.items():
            print(f"  {k}: {v}")
    else:
        print("  SEM DADOS")
    
    print("\n" + "=" * 80)
    print("3. DADOS DO WEMERSON (wemerson.barbosa@v4company.com) - Abril 2026")
    print("=" * 80)
    sql = """SELECT 
        email_investidor, cargo, senioridade, level,
        fixo_remuneracao_fixa, fixo_csp_esperado, fixo_churn_maximo_percentual,
        fixo_mrr_minimo, fixo_mrr_esperado, fixo_mrr_teto,
        fixo_mrr_atual, fixo_mrr_entrega, fixo_mrr_projeto_total,
        fixo_churn_atual, fixo_churn_maximo_valor,
        fixo_remuneracao_minima, fixo_remuneracao_maxima,
        calc_churn_real_percentual, calc_delta_churn_percentual, calc_delta_churn_valor,
        calc_variavel_churn, calc_delta_csp, calc_variavel_csp,
        calc_variavel_total, calc_remuneracao_total
    FROM plataforma_geral.investidores_metricas_mensais_novo 
    WHERE email_investidor = 'wemerson.barbosa@v4company.com' AND mes = 4 AND ano = 2026"""
    res = conn.execute(text(sql))
    row = res.mappings().first()
    if row:
        for k, v in row.items():
            print(f"  {k}: {v}")
    else:
        print("  SEM DADOS")

    print("\n" + "=" * 80)
    print("4. DADOS DO ISAAC (isaac.emanuel@v4company.com) - Abril 2026")
    print("=" * 80)
    sql = """SELECT 
        email_investidor, cargo, senioridade, level,
        fixo_remuneracao_fixa, fixo_csp_esperado, fixo_churn_maximo_percentual,
        fixo_mrr_minimo, fixo_mrr_esperado, fixo_mrr_teto,
        fixo_mrr_atual, fixo_mrr_entrega, fixo_mrr_projeto_total,
        fixo_churn_atual, fixo_churn_maximo_valor,
        fixo_remuneracao_minima, fixo_remuneracao_maxima,
        calc_churn_real_percentual, calc_delta_churn_percentual, calc_delta_churn_valor,
        calc_variavel_churn, calc_delta_csp, calc_variavel_csp,
        calc_variavel_total, calc_remuneracao_total
    FROM plataforma_geral.investidores_metricas_mensais_novo 
    WHERE email_investidor = 'isaac.emanuel@v4company.com' AND mes = 4 AND ano = 2026"""
    res = conn.execute(text(sql))
    row = res.mappings().first()
    if row:
        for k, v in row.items():
            print(f"  {k}: {v}")
    else:
        print("  SEM DADOS")

    print("\n" + "=" * 80)
    print("5. SIMULAÇÃO MANUAL DA FÓRMULA DO BANCO PARA OTÁVIO")
    print("=" * 80)
    sql = """SELECT fixo_mrr_atual, fixo_churn_atual, fixo_remuneracao_fixa, 
             fixo_csp_esperado, fixo_churn_maximo_percentual
    FROM plataforma_geral.investidores_metricas_mensais_novo 
    WHERE email_investidor = 'otavio.augusto@v4company.com' AND mes = 4 AND ano = 2026"""
    res = conn.execute(text(sql))
    row = res.first()
    if row:
        mrr_atual = float(row[0] or 0)
        churn_atual = float(row[1] or 0)
        fixo = float(row[2] or 0)
        csp_esp = float(row[3] or 0)
        churn_max_pct = float(row[4] or 0)
        
        print(f"  Inputs:")
        print(f"    fixo_mrr_atual = {mrr_atual}")
        print(f"    fixo_churn_atual = {churn_atual}")
        print(f"    fixo_remuneracao_fixa = {fixo}")
        print(f"    fixo_csp_esperado = {csp_esp}")
        print(f"    fixo_churn_maximo_percentual = {churn_max_pct}")
        
        if mrr_atual != 0:
            churn_real_pct = churn_atual / mrr_atual
            delta_churn_pct = churn_max_pct - churn_real_pct
            delta_churn_valor = delta_churn_pct * mrr_atual
            variavel_churn = delta_churn_valor * csp_esp
            
            csp_real = fixo / mrr_atual
            delta_csp = csp_esp - csp_real
            variavel_csp = delta_csp * mrr_atual
            
            variavel_total = variavel_csp + variavel_churn
            remuneracao_total = fixo + variavel_total
            
            print(f"\n  Cálculos:")
            print(f"    churn_real_pct = {churn_atual} / {mrr_atual} = {churn_real_pct}")
            print(f"    delta_churn_pct = {churn_max_pct} - {churn_real_pct} = {delta_churn_pct}")
            print(f"    delta_churn_valor = {delta_churn_pct} * {mrr_atual} = {delta_churn_valor}")
            print(f"    variavel_churn = {delta_churn_valor} * {csp_esp} = {variavel_churn}")
            print(f"    csp_real = {fixo} / {mrr_atual} = {csp_real}")
            print(f"    delta_csp = {csp_esp} - {csp_real} = {delta_csp}")
            print(f"    variavel_csp = {delta_csp} * {mrr_atual} = {variavel_csp}")
            print(f"    variavel_total = {variavel_csp} + {variavel_churn} = {variavel_total}")
            print(f"    remuneracao_total = {fixo} + {variavel_total} = {remuneracao_total}")
        else:
            print("  MRR ATUAL É 0 - Colunas calculadas serão NULL!")

    print("\n" + "=" * 80)
    print("6. TODOS OS INVESTIDORES - RESUMO ABRIL 2026")
    print("=" * 80)
    sql = """SELECT 
        email_investidor, cargo,
        fixo_mrr_atual, fixo_mrr_entrega, fixo_mrr_projeto_total,
        fixo_remuneracao_fixa, fixo_remuneracao_minima, fixo_remuneracao_maxima,
        calc_remuneracao_total
    FROM plataforma_geral.investidores_metricas_mensais_novo 
    WHERE mes = 4 AND ano = 2026 AND ativo = true
    ORDER BY email_investidor"""
    res = conn.execute(text(sql))
    for row in res:
        d = dict(zip(res.keys(), row))
        mrr_atual = float(d['fixo_mrr_atual'] or 0)
        mrr_total = float(d['fixo_mrr_projeto_total'] or 0)
        rem_total = float(d['calc_remuneracao_total'] or 0)
        rem_min = float(d['fixo_remuneracao_minima'] or 0)
        rem_max = float(d['fixo_remuneracao_maxima'] or 0)
        
        status = ""
        if rem_total <= 0:
            status = " !!! SEM CALCULO (MRR=0?)"
        elif rem_total <= rem_min:
            status = " !!! ABAIXO DO MINIMO"
        elif rem_total >= rem_max:
            status = " !!! NO TETO"
        
        print(f"  {d['email_investidor'][:30]:30s} | {d['cargo'] or '?':20s} | MRR Atual: {mrr_atual:>12,.2f} | MRR Total: {mrr_total:>12,.2f} | Rem: {rem_total:>10,.2f} (min: {rem_min:>10,.2f} max: {rem_max:>10,.2f}){status}")
