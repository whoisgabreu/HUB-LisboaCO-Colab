from sqlalchemy import extract, and_, desc, text
from database import Session
from models import (
    Investidor, InvestidorProjeto,
    MetricaMensal, RemuneracaoCargo
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
        # 0. Sincronizar status de atividade (Bulk Update)
        # Garante que MetricaMensal reflita o status atual do Investidor para o filtro na UI
        db.execute(text("""
            UPDATE plataforma_geral.investidores_metricas_mensais_novo m
            SET ativo = i.ativo
            FROM plataforma_geral.investidores i
            WHERE m.email_investidor = i.email
        """))

        # 1. Buscar Investidores (exceto Gerência via posição e apenas ATIVOS para cálculo)
        # REGRA: Apenas investidores com 'funcao' preenchida são considerados no cálculo.
        investidores = db.query(Investidor).filter(
            Investidor.ativo == True,
            Investidor.funcao != None,
            Investidor.funcao != ""
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
            # 0. Carregar a métrica primeiro para poder acessar o historico_projetos
            metrica = db.query(MetricaMensal).filter(
                MetricaMensal.email_investidor == inv.email,
                MetricaMensal.mes == mes,
                MetricaMensal.ano == ano
            ).first()

            hist_map = {}
            if metrica and metrica.historico_projetos:
                hist_map = {str(item.get("projeto_id")): item for item in metrica.historico_projetos}

            # 1. MRR Total da Carteira (Gross Fees Potencial)
            mrr_portfolio_total = Decimal("0.0")
            
            # 2. Churn
            churn_atual = Decimal("0.0")
            
            detalhes = []
            fees_calculados = {} # Salva o fee processado (proporcional + USD + Cientista) por projeto

            # Buscar vínculos para calcular o MRR Total e detalhamento
            vinculos = db.query(InvestidorProjeto).filter(
                InvestidorProjeto.email_investidor == inv.email
            ).all()
            
            for v in vinculos:
                pid = str(v.pipefy_id_projeto)
                # Achar a moeda do projeto
                from models import ProjetoAtivo, ProjetoOnetime
                proj_ativo = db.query(ProjetoAtivo).filter_by(pipefy_id=v.pipefy_id_projeto).first()
                if not proj_ativo:
                    proj_ativo = db.query(ProjetoOnetime).filter_by(pipefy_id=v.pipefy_id_projeto).first()
                
                moeda = proj_ativo.moeda if proj_ativo else "BRL"

                # Define o fee base
                hist_item = hist_map.get(pid)
                if hist_item:
                    # valor_proporcional JÁ CONTÉM o bônus cientista (aplicado em projeto_participacao_service)
                    fee_full = Decimal(str(hist_item.get("valor_proporcional", 0)))
                else:
                    # Fallback caso não tenha rodado o service de participação
                    fee_full = Decimal(str(v.fee_projeto or 0))
                    if v.cientista:
                        fee_full *= Decimal("1.5")

                # Conversão de moeda sempre é feita no final (hist_item não converte USD)
                if moeda == "USD":
                    from services.currency import CurrencyService
                    rate = CurrencyService.get_usd_to_brl_rate()
                    fee_full *= rate
                
                # Arredonda
                fee_full = fee_full.quantize(Decimal("0.01"))
                fees_calculados[pid] = fee_full

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

            # Buscar limites do cargo
            cargo_config = None
            if inv.funcao and inv.senioridade and inv.nivel:
                cargo_config = cargos_index.get((inv.funcao, inv.senioridade, inv.nivel))
            
            flag = "YELLOW"
            motivo_flag = ""
            if cargo_config:
                mrr_min = cargo_config.calc_mrr_minima or Decimal("0")
                mrr_esperado = cargo_config.fixo_mrr_esperado or Decimal("0")
                mrr_teto = cargo_config.fixo_mrr_teto or Decimal("0")
                churn_max_valor = cargo_config.calc_churn_maximo_valor or Decimal("0")

                # REGRA DE FLAG: baseada no MRR do portfólio
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
            metrica.ativo = True
            
            # ATRIBUIÇÃO FINAL — remuneração baseada em entregas
            metrica.fixo_mrr_projeto_total = mrr_portfolio_total
            
            # Calcula MRR entregue POR PROJETO: fee_projeto × progresso_projeto
            is_criativo = metrica.cargo in ("Designer", "WebDesigner", "Webdesigner")
            entregas = metrica.entregas_criativos if is_criativo else metrica.entregas_operacao
            entregas = entregas or []
            
            # Cria um mapa de entregas por projeto_id para busca rápida
            entregas_map = {str(p.get("projeto_id")): p for p in entregas if p.get("projeto_id")}

            novo_mrr = Decimal("0")
            for v in vinculos:
                if not v.active:
                    continue

                pid = str(v.pipefy_id_projeto)
                p = entregas_map.get(pid)
                
                progresso = Decimal("0")
                if p:
                    # Calcula o progresso deste projeto
                    if is_criativo:
                        c_c = p.get('criativos', {}).get('contratados', 0)
                        c_e = p.get('criativos', {}).get('entregues', 0)
                        v_c = p.get('videos', {}).get('contratados', 0)
                        v_e = p.get('videos', {}).get('entregues', 0)
                        l_c = p.get('lp', {}).get('contratados', 0)
                        l_e = p.get('lp', {}).get('entregues', 0)
                        t_meta = c_c + v_c + l_c
                        t_feito = c_e + v_e + l_e
                        # Regra: Se meta é 0, ganha 100%
                        progresso = min(Decimal(str(t_feito / t_meta)), Decimal("1.0")) if t_meta > 0 else Decimal("1")
                    else:
                        itens = p.get('entregas', [])
                        t_meta = sum(item.get('meta', 0) for item in itens)
                        t_feito = sum(item.get('entregues', 0) for item in itens)
                        progresso = min(Decimal(str(t_feito / t_meta)), Decimal("1.0")) if t_meta > 0 else Decimal("0")
                else:
                    # Regra: Se não está na lista (não definido), Designer ganha 100%
                    if is_criativo:
                        progresso = Decimal("1")
                    else:
                        progresso = Decimal("0") # Operação exige checklist para contar MRR

                fee_proj = fees_calculados.get(pid, Decimal("0"))

                # Contribuição = fee proporcional × progresso do projeto
                novo_mrr += fee_proj * progresso
            
            metrica.fixo_mrr_entrega = novo_mrr # MRR bruto entregue
            metrica.fixo_mrr_atual = novo_mrr - churn_atual # MRR atual descontando churn
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

            # Flush individual para evitar bulk INSERT/UPDATE problemático com colunas GENERATED (FetchedValue)
            db.flush()

        db.commit()
