from django.db import connection, transaction
from django.db.models import F, Q
from decimal import Decimal
from datetime import datetime, date
from django.utils import timezone
from users.models import Investidor
from projetos.models import InvestidorProjeto, ProjetoAtivo, ProjetoOnetime
from remuneracao.models import MetricaMensal, RemuneracaoCargo
from services.currency import CurrencyService

def calcular_metricas_mensais(mes, ano):
    """
    Serviço de remuneração centralizado e padronizado em Unidades (Reais).
    Lógica baseada no vínculo direto em investidores_projetos.
    Migrado de Flask/SQLAlchemy para Django ORM.
    """
    with transaction.atomic():
        # 0. Sincronizar status de atividade (Bulk Update)
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE plataforma_geral.investidores_metricas_mensais_novo m
                SET ativo = i.ativo
                FROM plataforma_geral.investidores i
                WHERE m.email_investidor = i.email
            """)

        # 1. Buscar Investidores (exceto Gerência via posição e apenas ATIVOS para cálculo)
        investidores = Investidor.objects.filter(
            ativo=True,
            funcao__isnull=False
        ).exclude(funcao="")

        # 2. Indexar Cargos para limites
        cargos_all = RemuneracaoCargo.objects.all()
        cargos_index = {
            (c.fixo_cargo, c.fixo_senioridade, c.fixo_level): c
            for c in cargos_all
        }

        # Mês atual para Churn
        mes_atual_str = f"{ano}-{mes:02d}"

        for inv in investidores:
            mrr_portfolio_total = Decimal("0.0")
            churn_atual = Decimal("0.0")
            detalhes = []

            # 3. Buscar vínculos para calcular o MRR Total e detalhamento
            vinculos = InvestidorProjeto.objects.filter(email_investidor=inv.email)
            
            for v in vinculos:
                # Achar a moeda do projeto
                proj = ProjetoAtivo.objects.filter(pipefy_id=v.pipefy_id_projeto).first()
                if not proj:
                    proj = ProjetoOnetime.objects.filter(pipefy_id=v.pipefy_id_projeto).first()
                
                moeda = proj.moeda if proj else "BRL"
                fee_full = Decimal(str(v.fee_projeto or 0))

                # Conversão
                if moeda == "USD":
                    rate = CurrencyService.get_usd_to_brl_rate()
                    fee_full *= rate
                
                # Regra do Cientista
                if v.cientista:
                    fee_full *= Decimal("1.5")
                
                if v.active:
                    mrr_portfolio_total += fee_full
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
                    if v.inactivated_at and v.inactivated_at.strftime("%Y-%m") == mes_atual_str:
                        churn_atual += fee_full

            # 4. Buscar limites do cargo
            cargo_config = cargos_index.get((inv.funcao, inv.senioridade, inv.nivel))
            
            flag = "YELLOW"
            motivo_flag = ""
            if cargo_config:
                mrr_min = cargo_config.calc_mrr_minima or Decimal("0")
                mrr_teto = cargo_config.fixo_mrr_teto or Decimal("0")
                churn_max_valor = cargo_config.calc_churn_maximo_valor or Decimal("0")

                is_green = (churn_atual <= churn_max_valor and 
                            mrr_portfolio_total >= mrr_min and 
                            mrr_portfolio_total <= mrr_teto)
                
                if is_green:
                    flag = "GREEN"
                    motivo_flag = "Dentro dos parâmetros (GREEN)"
                else:
                    motivos = []
                    if churn_atual > churn_max_valor:
                        motivos.append(f"Churn acima do máximo ({float(churn_atual):.2f} > {float(churn_max_valor):.2f})")
                    if mrr_portfolio_total < mrr_min:
                        motivos.append(f"MRR Portfolio ({float(mrr_portfolio_total):.2f}) abaixo do mínimo ({float(mrr_min):.2f})")
                    if mrr_portfolio_total > mrr_teto:
                        motivos.append(f"MRR Portfolio ({float(mrr_portfolio_total):.2f}) acima do teto ({float(mrr_teto):.2f})")
                    motivo_flag = " | ".join(motivos) if motivos else "Abaixo do MRR mínimo"
            else:
                if inv.posicao == "Sócio" and not inv.funcao:
                    flag = "GREEN"
                    motivo_flag = "Sócio sem cargo operacional"
                else:
                    motivo_flag = "Cargo/Nível não configurado"

            # 5. Lógica de Streaks
            historico = MetricaMensal.objects.filter(
                email_investidor=inv.email
            ).order_by('-ano', '-mes').first()

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

            # 6. Upsert na MetricaMensal
            metrica, created = MetricaMensal.objects.get_or_create(
                email_investidor=inv.email,
                mes=mes,
                ano=ano
            )

            # Preencher campos
            metrica.detalhes = {"produtos": detalhes}
            metrica.cargo = inv.funcao
            metrica.senioridade = inv.senioridade
            metrica.level = inv.nivel
            metrica.flag = flag
            metrica.motivo_flag = motivo_flag
            metrica.green_streak = green_streak
            metrica.yellow_streak = yellow_streak
            metrica.ativo = True
            
            metrica.fixo_mrr_atual = mrr_portfolio_total
            metrica.fixo_mrr_entrega = mrr_portfolio_total
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

            metrica.save()
