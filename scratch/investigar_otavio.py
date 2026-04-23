"""
Investigação detalhada do Otávio:
- Cargo/Senioridade/Level no banco
- Cargo config da tabela remuneracao_cargos
- Entregas operação detalhadas (progresso por projeto)
- Vínculos ativos
"""
import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text
import json

with engine.connect() as conn:
    print("=" * 80)
    print("1. INVESTIDOR - OTAVIO")
    print("=" * 80)
    sql = "SELECT * FROM plataforma_geral.investidores WHERE email = 'otavio.augusto@v4company.com'"
    res = conn.execute(text(sql))
    cols = res.keys()
    for row in res:
        d = dict(zip(cols, row))
        for k, v in d.items():
            print(f"  {k}: {v}")

    print("\n" + "=" * 80)
    print("2. METRICA MENSAL - CARGO/SENIORIDADE/LEVEL GRAVADOS")
    print("=" * 80)
    sql = """SELECT cargo, senioridade, level, fixo_csp_esperado, fixo_remuneracao_fixa,
             fixo_mrr_esperado, fixo_mrr_teto, fixo_remuneracao_minima, fixo_remuneracao_maxima,
             fixo_churn_maximo_percentual
    FROM plataforma_geral.investidores_metricas_mensais_novo 
    WHERE email_investidor = 'otavio.augusto@v4company.com' AND mes = 4 AND ano = 2026"""
    res = conn.execute(text(sql))
    row = res.mappings().first()
    if row:
        for k, v in row.items():
            print(f"  {k}: {v}")

    print("\n" + "=" * 80)
    print("3. CONFIGURACAO DO CARGO (remuneracao_cargos) - Gestor de Trafego Pleno L3")
    print("=" * 80)
    sql = """SELECT * FROM plataforma_geral.remuneracao_cargos 
    WHERE fixo_cargo = 'Gestor de Trafego' AND fixo_senioridade = 'Pleno' AND fixo_level = 'L3'"""
    res = conn.execute(text(sql))
    row = res.mappings().first()
    if row:
        for k, v in row.items():
            print(f"  {k}: {v}")
    else:
        # Tenta com acento
        sql2 = """SELECT * FROM plataforma_geral.remuneracao_cargos 
        WHERE fixo_cargo LIKE 'Gestor%%' AND fixo_senioridade = 'Pleno' AND fixo_level = 'L3'"""
        res2 = conn.execute(text(sql2))
        row2 = res2.mappings().first()
        if row2:
            for k, v in row2.items():
                print(f"  {k}: {v}")
        else:
            print("  NAO ENCONTRADO!")

    print("\n" + "=" * 80)
    print("4. VINCULOS ATIVOS DO OTAVIO (investidores_projetos)")
    print("=" * 80)
    sql = """SELECT pipefy_id_projeto, nome_projeto, fee_projeto, active, cientista
    FROM plataforma_geral.investidores_projetos 
    WHERE email_investidor = 'otavio.augusto@v4company.com'
    ORDER BY active DESC, nome_projeto"""
    res = conn.execute(text(sql))
    total_fee_ativo = 0
    for row in res:
        d = dict(zip(res.keys(), row))
        fee = float(d['fee_projeto'] or 0)
        if d['active']:
            total_fee_ativo += fee
        print(f"  [{('ATIVO' if d['active'] else 'INATIVO'):7s}] {d['nome_projeto'] or '?':40s} | Fee: {fee:>10,.2f} | Cientista: {d['cientista']}")
    print(f"\n  TOTAL FEE ATIVOS: {total_fee_ativo:,.2f}")

    print("\n" + "=" * 80)
    print("5. ENTREGAS OPERACAO DO OTAVIO (JSON detalhado)")
    print("=" * 80)
    sql = """SELECT entregas_operacao FROM plataforma_geral.investidores_metricas_mensais_novo 
    WHERE email_investidor = 'otavio.augusto@v4company.com' AND mes = 4 AND ano = 2026"""
    res = conn.execute(text(sql))
    row = res.first()
    if row and row[0]:
        entregas = row[0]
        for p in entregas:
            pid = p.get('projeto_id', '?')
            cliente = p.get('cliente', '?')
            itens = p.get('entregas', [])
            total_meta = sum(i.get('meta', 0) for i in itens)
            total_entregues = sum(i.get('entregues', 0) for i in itens)
            pct = (total_entregues / total_meta * 100) if total_meta > 0 else 0
            print(f"  Projeto {pid} ({cliente})")
            for item in itens:
                print(f"    - {item.get('tipo', '?'):30s} | Meta: {item.get('meta', 0):3d} | Entregues: {item.get('entregues', 0):3d}")
            print(f"    PROGRESSO: {total_entregues}/{total_meta} = {pct:.1f}%")
            print()
    else:
        print("  SEM ENTREGAS OPERACAO DEFINIDAS")

    print("\n" + "=" * 80)
    print("6. SIMULACAO: MRR ENTREGUE COM REGRA DE 100% PARA SEM-ENTREGAS")
    print("=" * 80)
    # Pega vinculos ativos
    sql = """SELECT pipefy_id_projeto, fee_projeto, cientista
    FROM plataforma_geral.investidores_projetos 
    WHERE email_investidor = 'otavio.augusto@v4company.com' AND active = true"""
    vinculos = conn.execute(text(sql)).fetchall()
    
    # Pega entregas
    sql = """SELECT entregas_operacao FROM plataforma_geral.investidores_metricas_mensais_novo 
    WHERE email_investidor = 'otavio.augusto@v4company.com' AND mes = 4 AND ano = 2026"""
    row = conn.execute(text(sql)).first()
    entregas = row[0] if row and row[0] else []
    entregas_map = {str(p.get('projeto_id')): p for p in entregas if p.get('projeto_id')}
    
    total_mrr = 0
    for v in vinculos:
        pid = str(v[0])
        fee = float(v[1] or 0)
        cientista = v[2]
        if cientista:
            fee *= 1.5
        
        p = entregas_map.get(pid)
        if p:
            itens = p.get('entregas', [])
            t_meta = sum(i.get('meta', 0) for i in itens)
            t_feito = sum(i.get('entregues', 0) for i in itens)
            pct = min(t_feito / t_meta, 1.0) if t_meta > 0 else 0
            contribuicao = fee * pct
            print(f"  Projeto {pid}: fee={fee:>10,.2f} * progresso={pct:.2%} = {contribuicao:>10,.2f} (TEM ENTREGAS)")
        else:
            # Gestor de Trafego sem entregas definidas = 0% (operacao exige checklist)
            contribuicao = 0
            print(f"  Projeto {pid}: fee={fee:>10,.2f} * progresso=0.00% = {contribuicao:>10,.2f} (SEM ENTREGAS - OPERACAO)")
        total_mrr += contribuicao
    
    print(f"\n  MRR ENTREGUE SIMULADO: {total_mrr:,.2f}")
    print(f"  CHURN: 0.00")
    print(f"  MRR ATUAL SIMULADO: {total_mrr:,.2f}")
    
    # Simula remuneracao
    fixo = 3750.0
    csp_esp = 0.0585938
    churn_max = 0.06
    if total_mrr > 0:
        var_csp = (csp_esp - fixo / total_mrr) * total_mrr
        var_churn = (churn_max - 0 / total_mrr) * total_mrr * csp_esp
        var_total = var_csp + var_churn
        rem_total = fixo + var_total
        print(f"\n  REMUNERACAO SIMULADA: {rem_total:,.2f}")
        print(f"  MIN: 2343.75 | MAX: 5156.25")
        if rem_total > 5156.25:
            print(f"  --> CLAMPADO NO TETO: 5156.25")
        elif rem_total < 2343.75:
            print(f"  --> CLAMPADO NO MINIMO: 2343.75")
