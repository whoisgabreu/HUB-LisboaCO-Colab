from sqlalchemy import extract, and_, desc
from database import Session
from models import (
    Investidor, InvestidorProjeto, 
    MetricaMensal, OperacaoEntregaMensal, RemuneracaoCargo
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
            mrr_atual = Decimal("0.0")
            mrr_projeto_total = Decimal("0.0")
            churn_atual = Decimal("0.0")
            detalhes = []

            # 3. Buscar vínculos diretamente com dados centralizados
            vinculos = db.query(InvestidorProjeto).filter(
                InvestidorProjeto.email_investidor == inv.email
            ).all()
            
            for v in vinculos:
                # # O Fee já está em unidades (Decimal) vindo de InvestidorProjeto
                # fee = Decimal(str(v.fee_projeto or 0)) ## Voltar a pegar fee_projeto caso reclamem da alteração
                # O Fee já está em unidades (Decimal) vindo de InvestidorProjeto (usando fee_contribuicao)
                fee = Decimal(str(v.fee_contribuicao or 0))
                
                # Regra do Cientista (aplica multiplicador sobre o fee base)
                if v.cientista:
                    fee *= Decimal("1.5")
                
                # Detalhes (snapshot para o JSON)
                detalhes.append({
                    "id": v.pipefy_id_projeto,
                    "nome": v.nome_projeto,
                    "cientista": v.cientista,
                    "ativo": v.active,
                    "fee": float(fee)
                })

                if v.active:
                    mrr_atual += fee
                    mrr_projeto_total += Decimal(str(v.fee_projeto or 0))
                else:
                    # Churn: se inativado no mês atual
                    if v.inactivated_at:
                        if v.inactivated_at.strftime("%Y-%m") == mes_atual_str:
                            # Churn usa o fee_projeto integral conforme solicitação
                            fee_churn = Decimal(str(v.fee_projeto or 0))
                            
                            # Mantém a regra do cientista caso se aplique
                            if v.cientista:
                                fee_churn *= Decimal("1.5")
                                
                            churn_atual += fee_churn

            # Buscar limites do cargo
            cargo_config = cargos_index.get((inv.funcao, inv.senioridade, inv.nivel))
            
            flag = "YELLOW"
            motivo_flag = ""
            if cargo_config:
                mrr_min = cargo_config.calc_mrr_minima or Decimal("0")
                mrr_esperado = cargo_config.fixo_mrr_esperado or Decimal("0")
                mrr_teto = cargo_config.fixo_mrr_teto or Decimal("0")
                churn_max_valor = cargo_config.calc_churn_maximo_valor or Decimal("0")

                # Regra de Flag:
                # is_green = churn_atual <= churn_max_valor AND mrr_atual >= mrr_min AND mrr_atual <= mrr_teto
                is_green = (churn_atual <= churn_max_valor and 
                            mrr_atual >= mrr_min and 
                            mrr_atual <= mrr_teto)
                
                if is_green:
                    flag = "GREEN"
                    motivo_flag = "Dentro dos parâmetros (GREEN)"
                else:
                    motivos = []
                    if churn_atual > churn_max_valor:
                        motivos.append(f"Churn acima do máximo ({float(churn_atual):.2f} > {float(churn_max_valor):.2f})")
                    if mrr_atual < mrr_min:
                        motivos.append(f"MRR abaixo do mínimo ({float(mrr_atual):.2f} < {float(mrr_min):.2f})")
                    if mrr_atual > mrr_teto:
                        motivos.append(f"MRR acima do teto ({float(mrr_atual):.2f} > {float(mrr_teto):.2f})")
                    motivo_flag = " | ".join(motivos) if motivos else "Abaixo do MRR mínimo"
            else:
                motivo_flag = "Cargo/Nível não configurado"

            # MRR Entrega (de Operação) - Já migrado para unidades na Fase 5
            soma_entrega = db.query(OperacaoEntregaMensal).filter(
                OperacaoEntregaMensal.investidor_email == inv.email,
                OperacaoEntregaMensal.mes == mes,
                OperacaoEntregaMensal.ano == ano
            ).all()
            total_entrega = sum(Decimal(str(e.valor_contribuicao_mrr or 0)) for e in soma_entrega)

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
                # Verificar se é o mês consecutivo (N8N logic)
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
                    # Não consecutivo
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
            
            metrica.fixo_mrr_atual = mrr_atual
            metrica.fixo_mrr_projeto_total = mrr_projeto_total
            metrica.fixo_mrr_entrega = total_entrega
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
