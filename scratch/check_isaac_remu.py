import sys
import os
sys.path.append(os.getcwd())
from database import Session
from models import MetricaMensal, Investidor
from decimal import Decimal

with Session() as db:
    # Pedro (Isaac) email
    email = 'contato@pedroisaac.com.br' # Assuming this from context or checking
    # Let's find him
    user = db.query(Investidor).filter(Investidor.nome.ilike('%Isaac%')).first()
    if not user:
        print("Usuário não encontrado")
    else:
        print(f"Usuário: {user.nome} ({user.email})")
        m = db.query(MetricaMensal).filter_by(email_investidor=user.email).order_by(MetricaMensal.ano.desc(), MetricaMensal.mes.desc()).first()
        if m:
            print(f"Mês/Ano: {m.mes}/{m.ano}")
            print(f"Fixo: {m.fixo_remuneracao_fixa}")
            print(f"MRR Atual (Entrega): {m.fixo_mrr_atual}")
            print(f"CSP Esp: {m.fixo_csp_esperado}")
            print(f"Churn Max: {m.fixo_churn_maximo_percentual}")
            print(f"Variável Total (DB): {m.calc_variavel_total}")
            print(f"Remuneração Total (DB): {m.calc_remuneracao_total}")
            
            # Simulando o cálculo do banco
            mrr = float(m.fixo_mrr_atual or 0)
            fixo = float(m.fixo_remuneracao_fixa or 0)
            csp_esp = float(m.fixo_csp_esperado or 0)
            
            if mrr > 0:
                real_csp = fixo / mrr
                delta_csp = csp_esp - real_csp
                bonus_csp = delta_csp * mrr
                print(f"Simulação CSP: {bonus_csp}")
            else:
                print("MRR é 0, sem bônus CSP")
        else:
            print("Métrica não encontrada")
