from sqlalchemy import extract, and_, desc
from database import Session
from models import (
    Investidor, InvestidorProjeto,
    MetricaMensal, MonthlyDelivery, RemuneracaoCargo
)
from decimal import Decimal
from datetime import datetime, date
import json

def calcular_metricas_mensais(mes, ano):
    """
    Serviço de remuneração centralizado e padronizado em Unidades (Reais).
    Lógica baseada no vínculo direto em investidores_projetos.
    """
    with Session() as db:
        # 1. Buscar Investidores (exceto Gerência)
        investidores = db.query(Investidor).filter(
            Investidor.ativo == True,
            Investidor.squad != "Gerência"
        ).all()

        # 2. Indexar Cargos para limites
        cargos_all = db.query(RemuneracaoCargo).all()
        cargos_index = {
            (c.fixo_cargo, c.fixo_senioridade, c.fixo_level): c
            for c in cargos_all
        }

        # Mês atual para Churn
        mes_atual_str = f"{ano}-{mes:02d}"

        for inv in investidores:
            # 1. MRR Total da Carteira (Gross Fees Potencial)
            # Conforme Step 9: fixo_mrr_atual é a soma de todos os fees ativos.
            mrr_portfolio_total = Decimal("0.0")
            
            # 2. Churn
            churn_atual = Decimal("0.0")
            
            detalhes = []

            # Buscar vínculos para calcular o MRR Total e detalhamento
            vinculos = db.query(InvestidorProjeto).filter(
                InvestidorProjeto.email_investidor == inv.email
            ).all()
            
            for v in vinculos:
                # Achar a moeda do projeto
                from models import ProjetoAtivo, ProjetoOnetime
                proj_ativo = db.query(ProjetoAtivo).filter_by(pipefy_id=v.pipefy_id_projeto).first()
                if not proj_ativo:
                    proj_ativo = db.query(ProjetoOnetime).filter_by(pipefy_id=v.pipefy_id_projeto).first()
                
                moeda = proj_ativo.moeda if proj_ativo else "BRL"

                # O Fee do projeto bruto (Total Portfolio)
                fee_full = Decimal(str(v.fee_projeto or 0))

                # Conversão
                if moeda == "USD":
                    from services.currency import CurrencyService
                    rate = CurrencyService.get_usd_to_brl_rate()
                    fee_full *= rate
                
                # Regra do Cientista (aplica multiplicador sobre o fee base para o portfólio)
                if v.cientista:
                    fee_full *= Decimal("1.5")
                
                if v.active:
                    mrr_portfolio_total += fee_full
                    
                    # Detalhes (snapshot para o JSON)
                    detalhes.append({
                        "id": v.pipefy_id_projeto,
                        "nome": v.nome_projeto,
                        "moeda": moeda,
                        "cientista": v.cientista,
                        "ativo": v.active,
                        "fee": float(fee_full)
                    })
                else:
                    # Churn: se inativado no mês atual
                    if v.inactivated_at:
                        if v.inactivated_at.strftime("%Y-%m") == mes_atual_str:
                            churn_atual += fee_full

            # 3. MRR Trabalhado (Dashboard)
            # Conforme solicitado, este valor vem das entregas mas NÃO é a base do cálculo SQL (fixo_mrr_atual)
            soma_entrega = db.query(MonthlyDelivery).filter(
                MonthlyDelivery.email == inv.email,
                MonthlyDelivery.month == mes,
                MonthlyDelivery.year == ano,
                MonthlyDelivery.status == 'completed',
            ).all()
            mrr_trabalhado = sum(Decimal(str(e.mrr_contribution or 0)) for e in soma_entrega)

            # Buscar limites do cargo
            cargo_config = cargos_index.get((inv.funcao, inv.senioridade, inv.nivel))
            
            flag = "YELLOW"
            motivo_flag = ""
            if cargo_config:
                mrr_min = cargo_config.calc_mrr_minima or Decimal("0")
                mrr_esperado = cargo_config.fixo_mrr_esperado or Decimal("0")
                mrr_teto = cargo_config.fixo_mrr_teto or Decimal("0")
                churn_max_valor = cargo_config.calc_churn_maximo_valor or Decimal("0")

                # REGRA DE FLAG: O usuário solicitou que a flag seja baseada no MRR TRABALHADO
                is_green = (churn_atual <= churn_max_valor and 
                            mrr_trabalhado >= mrr_min and 
                            mrr_trabalhado <= mrr_teto)
                
                if is_green:
                    flag = "GREEN"
                    motivo_flag = "Dentro dos parâmetros (GREEN)"
                else:
                    motivos = []
                    if churn_atual > churn_max_valor:
                        motivos.append(f"Churn acima do máximo ({float(churn_atual):.2f} > {float(churn_max_valor):.2f})")
                    if mrr_trabalhado < mrr_min:
                        motivos.append(f"MRR Trabalhado ({float(mrr_trabalhado):.2f}) abaixo do mínimo ({float(mrr_min):.2f})")
                    if mrr_trabalhado > mrr_teto:
                        motivos.append(f"MRR Trabalhado ({float(mrr_trabalhado):.2f}) acima do teto ({float(mrr_teto):.2f})")
                    motivo_flag = " | ".join(motivos) if motivos else "Abaixo do MRR mínimo"
            else:
                motivo_flag = "Cargo/Nível não configurado"

            # Lógica de Streaks
            historico = db.query(MetricaMensal).filter(
                MetricaMensal.email_investidor == inv.email
            ).order_by(desc(MetricaMensal.ano), desc(MetricaMensal.mes)).first()

            green_streak = 0
            yellow_streak = 0

            if not historico:
                green_streak = 1 if flag == "GREEN" else 0
                yellow_streak = 1 if flag == "YELLOW" else 0
            else:
                mes_esp = mes - 1
                ano_esp = ano
                if mes == 1:
                    mes_esp = 12
                    ano_esp = ano - 1
                
                eh_consecutivo = (historico.mes == mes_esp and historico.ano == ano_esp)
                
                if eh_consecutivo:
                    if flag == "GREEN":
                        green_streak = (historico.green_streak or 0) + 1 if historico.flag == "GREEN" else 1
                        yellow_streak = 0
                    else: # YELLOW
                        yellow_streak = (historico.yellow_streak or 0) + 1 if historico.flag == "YELLOW" else 1
                        green_streak = 0
                else:
                    green_streak = 1 if flag == "GREEN" else 0
                    yellow_streak = 1 if flag == "YELLOW" else 0

            # Upsert na MetricaMensal
            metrica = db.query(MetricaMensal).filter(
                MetricaMensal.email_investidor == inv.email,
                MetricaMensal.mes == mes,
                MetricaMensal.ano == ano
            ).first()

            if not metrica:
                metrica = MetricaMensal(
                    email_investidor=inv.email,
                    mes=mes,
                    ano=ano
                )
                db.add(metrica)

            # Preencher campos
            metrica.detalhes = {"produtos": detalhes}
            metrica.cargo = inv.funcao
            metrica.senioridade = inv.senioridade
            metrica.level = inv.nivel
            metrica.flag = flag
            metrica.motivo_flag = motivo_flag
            metrica.green_streak = green_streak
            metrica.yellow_streak = yellow_streak
            
            # ATRIBUIÇÃO FINAL CONFORME SQL E STEP 9
            # ATRIBUIÇÃO FINAL CONFORME LOGICA_ENTREGAS.MD (Step 7)
            # fixo_mrr_atual: Base para o SQL (O usuário solicitou que seja o MRR Trabalhado)
            metrica.fixo_mrr_atual = mrr_trabalhado          
            # fixo_mrr_entrega: MRR Trabalhado para exibição no Dashboard (MRR Atual)
            metrica.fixo_mrr_entrega = mrr_trabalhado        
            # fixo_mrr_projeto_total: Comparativo do Portfólio
            metrica.fixo_mrr_projeto_total = mrr_portfolio_total 
            metrica.fixo_churn_atual = churn_atual
            if cargo_config:
                metrica.fixo_remuneracao_fixa = cargo_config.fixo_remuneracao_fixa
                metrica.fixo_csp_esperado = cargo_config.calc_csp_esperado
                metrica.fixo_churn_maximo_percentual = cargo_config.fixo_churn_maximo_percentual
                metrica.fixo_mrr_minimo = cargo_config.calc_mrr_minima
                metrica.fixo_mrr_esperado = cargo_config.fixo_mrr_esperado
                metrica.fixo_mrr_teto = cargo_config.fixo_mrr_teto
                metrica.fixo_churn_maximo_valor = cargo_config.calc_churn_maximo_valor
                metrica.fixo_remuneracao_minima = cargo_config.calc_remuneracao_minima
                metrica.fixo_remuneracao_maxima = cargo_config.calc_remuneracao_maxima

        db.commit()
