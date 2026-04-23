"""
Investigacao profunda do Otavio: comparacao entre tabela investidores 
e metricas_mensais, e validacao de cada fee por projeto.
"""
import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=" * 80)
    print("1. INVESTIDOR (tabela investidores) vs METRICA (tabela metricas)")
    print("=" * 80)
    
    sql = "SELECT funcao, senioridade, nivel, posicao, squad FROM plataforma_geral.investidores WHERE email = 'otavio.augusto@v4company.com'"
    inv = conn.execute(text(sql)).mappings().first()
    
    sql = "SELECT cargo, senioridade, level FROM plataforma_geral.investidores_metricas_mensais_novo WHERE email_investidor = 'otavio.augusto@v4company.com' AND mes = 4 AND ano = 2026"
    met = conn.execute(text(sql)).mappings().first()
    
    print(f"  INVESTIDORES TABLE:")
    print(f"    funcao: {inv['funcao']}")
    print(f"    senioridade: {inv['senioridade']}")
    print(f"    nivel: {inv['nivel']}")
    print(f"    posicao: {inv['posicao']}")
    print(f"    squad: {inv['squad']}")
    
    print(f"\n  METRICAS TABLE:")
    print(f"    cargo: {met['cargo']}")
    print(f"    senioridade: {met['senioridade']}")
    print(f"    level: {met['level']}")
    
    match = (inv['funcao'] == met['cargo'] and inv['senioridade'] == met['senioridade'] and inv['nivel'] == met['level'])
    print(f"\n  MATCH: {'SIM' if match else 'NAO - DIVERGENCIA!'}")

    print("\n" + "=" * 80)
    print("2. CONFIG DO CARGO (remuneracao_cargos)")
    print("=" * 80)
    sql = "SELECT * FROM plataforma_geral.remuneracao_cargos WHERE fixo_cargo = :cargo AND fixo_senioridade = :sen AND fixo_level = :lvl"
    cfg = conn.execute(text(sql), {"cargo": inv['funcao'], "sen": inv['senioridade'], "lvl": inv['nivel']}).mappings().first()
    if cfg:
        print(f"  fixo_cargo: {cfg['fixo_cargo']}")
        print(f"  fixo_senioridade: {cfg['fixo_senioridade']}")
        print(f"  fixo_level: {cfg['fixo_level']}")
        print(f"  fixo_remuneracao_fixa: {cfg['fixo_remuneracao_fixa']}")
        print(f"  fixo_mrr_esperado: {cfg['fixo_mrr_esperado']}")
        print(f"  fixo_mrr_teto: {cfg['fixo_mrr_teto']}")
        print(f"  calc_csp_esperado: {cfg['calc_csp_esperado']}")
        print(f"  fixo_churn_maximo_percentual: {cfg['fixo_churn_maximo_percentual']}")
        print(f"  calc_remuneracao_minima: {cfg['calc_remuneracao_minima']}")
        print(f"  calc_remuneracao_maxima: {cfg['calc_remuneracao_maxima']}")
    else:
        print("  NAO ENCONTRADO! Cargo/Senioridade/Level nao existe na tabela remuneracao_cargos!")

    print("\n" + "=" * 80)
    print("3. VALIDACAO FEE POR PROJETO (investidores_projetos vs detalhes JSON)")
    print("=" * 80)
    
    # Fees do vinculo
    sql = """SELECT pipefy_id_projeto, fee_projeto, cientista, active
    FROM plataforma_geral.investidores_projetos 
    WHERE email_investidor = 'otavio.augusto@v4company.com' AND active = true"""
    vinculos = conn.execute(text(sql)).fetchall()
    
    # Detalhes JSON
    sql = """SELECT detalhes FROM plataforma_geral.investidores_metricas_mensais_novo 
    WHERE email_investidor = 'otavio.augusto@v4company.com' AND mes = 4 AND ano = 2026"""
    det_row = conn.execute(text(sql)).first()
    detalhes = det_row[0].get('produtos', []) if det_row and det_row[0] else []
    det_map = {d['id']: d for d in detalhes}
    
    total_vinculo = 0
    total_detalhes = 0
    
    for v in vinculos:
        pid = v[0]
        fee_raw = float(v[1] or 0)
        cientista = v[2]
        
        # Busca moeda
        sql2 = "SELECT moeda FROM plataforma_geral.projetos_ativos WHERE pipefy_id = :pid"
        proj = conn.execute(text(sql2), {"pid": pid}).first()
        moeda = proj[0] if proj else "BRL"
        
        fee_calc = fee_raw
        if moeda == "USD":
            from services.currency import CurrencyService
            rate = float(CurrencyService.get_usd_to_brl_rate())
            fee_calc = fee_raw * rate
        if cientista:
            fee_calc = fee_calc * 1.5
        
        total_vinculo += fee_calc
        
        det = det_map.get(pid, {})
        fee_det = det.get('fee', 0)
        total_detalhes += fee_det
        
        diff = abs(fee_calc - fee_det)
        flag = " *** DIFF!" if diff > 1 else ""
        
        print(f"  Projeto {pid}: fee_raw={fee_raw:>10,.2f} | moeda={moeda} | cient={cientista} | fee_calc={fee_calc:>10,.2f} | det_fee={fee_det:>10,.2f}{flag}")
    
    print(f"\n  TOTAL vinculo calculado: {total_vinculo:>12,.2f}")
    print(f"  TOTAL detalhes JSON:    {total_detalhes:>12,.2f}")
    
    print("\n" + "=" * 80)
    print("4. RESUMO FINAL - POR QUE O OTAVIO ESTA NO TETO")
    print("=" * 80)
    
    sql = """SELECT fixo_mrr_atual, fixo_mrr_esperado, fixo_remuneracao_fixa, 
             fixo_csp_esperado, calc_remuneracao_total, fixo_remuneracao_maxima
    FROM plataforma_geral.investidores_metricas_mensais_novo 
    WHERE email_investidor = 'otavio.augusto@v4company.com' AND mes = 4 AND ano = 2026"""
    row = conn.execute(text(sql)).mappings().first()
    mrr = float(row['fixo_mrr_atual'] or 0)
    mrr_esp = float(row['fixo_mrr_esperado'] or 0)
    fixo = float(row['fixo_remuneracao_fixa'] or 0)
    csp_esp = float(row['fixo_csp_esperado'] or 0)
    rem = float(row['calc_remuneracao_total'] or 0)
    rem_max = float(row['fixo_remuneracao_maxima'] or 0)
    
    print(f"  MRR Atual: {mrr:,.2f}")
    print(f"  MRR Esperado (meta): {mrr_esp:,.2f}")
    print(f"  Diferenca: MRR excede meta em {mrr - mrr_esp:,.2f} ({(mrr/mrr_esp - 1)*100:.1f}%)")
    print(f"  Fixo: {fixo:,.2f}")
    print(f"  CSP Esperado: {csp_esp:.7f} ({csp_esp*100:.4f}%)")
    print(f"  CSP Real: {fixo/mrr:.7f} ({fixo/mrr*100:.4f}%)")
    print(f"  Rem calculada: {rem:,.2f}")
    print(f"  Rem maxima: {rem_max:,.2f}")
    print(f"  Acima do teto em: {rem - rem_max:,.2f}")
