import calendar
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy import extract, and_, or_
from database import Session
from sqlalchemy.orm.attributes import flag_modified
from models import MetricaMensal, InvestidorProjeto, ProjetoAtivo, ProjetoOnetime, ProjetoInativo

from collections import defaultdict
from .currency import CurrencyService


class ProjetoParticipacaoService:
    @staticmethod
    def get_total_days_in_month(mes, ano):
        """Retorna o total de dias no mês/ano especificado."""
        return calendar.monthrange(ano, mes)[1]

    @staticmethod
    def calcular_valor_proporcional(fee, data_inicio, data_fim, mes, ano):
        """
        Calcula o valor proporcional do fee baseado nos dias trabalhados no mês.
        Fórmula: X = (Dias Trabalhados * Fee) / Total de Dias no Mês
        """
        total_dias_mes = ProjetoParticipacaoService.get_total_days_in_month(mes, ano)
        
        # Filtra as datas para o mês de referência
        inicio_mes = date(ano, mes, 1)
        fim_mes = date(ano, mes, total_dias_mes)
        
        # Ajusta data_inicio e data_fim para ficarem dentro do mês de referência
        # Se data_fim for None (ativo), consideramos o fim do mês para o cálculo proporcional do mês atual
        data_fim_calc_val = data_fim if data_fim else fim_mes
        
        data_inicio_calc = max(data_inicio, inicio_mes)
        data_fim_calc = min(data_fim_calc_val, fim_mes)
        
        if data_inicio_calc > data_fim_calc:
            return Decimal("0.00")
            
        dias_trabalhados = (data_fim_calc - data_inicio_calc).days + 1
        
        if fee is None:
            fee = 0
            
        fee_decimal = Decimal(str(fee))
        valor_proporcional = (Decimal(dias_trabalhados) * fee_decimal) / Decimal(total_dias_mes)
        
        return valor_proporcional.quantize(Decimal("0.01"))

    @staticmethod
    def sincronizar_remuneracao(mes, ano):
        """
        Sincroniza todos os funcionários para o mês de referência usando investidores_projetos como fonte de verdade.
        Refatorado para processamento em lote por e-mail para garantir a captura de múltiplos projetos.
        """
        with Session() as db:
            # 1. Definir parâmetros do mês
            data_inicio_ref = date(ano, mes, 1)
            total_dias_mes = ProjetoParticipacaoService.get_total_days_in_month(mes, ano)
            data_fim_ref = date(ano, mes, total_dias_mes)
            
            # Regra de data inicial padrão para população inicial (Março 2026)
            data_inicio_baseline = date(2026, 3, 1)

            # 2. Buscar vínculos fonte de verdade: Ativos OU inativados no mês corrente
            vinculos = db.query(InvestidorProjeto).filter(
                or_(
                    InvestidorProjeto.active == True,
                    InvestidorProjeto.active == None,
                    and_(

                        InvestidorProjeto.active == False,
                        InvestidorProjeto.inactivated_at != None,
                        extract('month', InvestidorProjeto.inactivated_at) == mes,
                        extract('year', InvestidorProjeto.inactivated_at) == ano
                    )
                )
            ).all()

            # 3. Mapear moedas dos projetos (fonte: projetos_ativos, onetime, inativos)
            proj_ids = [v.pipefy_id_projeto for v in vinculos]
            moedas_map = {}
            
            # Busca em todas as tabelas de projetos para garantir que pegamos a moeda correta
            tabelas_projetos = [ProjetoAtivo, ProjetoOnetime, ProjetoInativo]
            for Model in tabelas_projetos:
                projs = db.query(Model.pipefy_id, Model.moeda).filter(Model.pipefy_id.in_(proj_ids)).all()
                for pid, moeda in projs:
                    if pid not in moedas_map:
                        m_str = str(moeda).strip().upper() if moeda else "BRL"
                        moedas_map[pid] = "USD" if m_str == "USD" else "BRL"


            # 4. Agrupar vínculos por e-mail

            vinculos_por_email = defaultdict(list)
            for v in vinculos:
                vinculos_por_email[v.email_investidor].append(v)

            # 4. Processar cada investidor que possui vínculos ou métricas no mês
            # Também buscamos métricas existentes para garantir que limpamos as que perderam todos os vínculos
            metricas_existentes = db.query(MetricaMensal).filter_by(mes=mes, ano=ano).all()
            emails_com_metrica = {m.email_investidor for m in metricas_existentes}
            todos_emails = set(vinculos_por_email.keys()) | emails_com_metrica

            for email in todos_emails:
                # Busca ou cria a métrica
                metrica = next((m for m in metricas_existentes if m.email_investidor == email), None)
                if not metrica:
                    metrica = MetricaMensal(
                        email_investidor=email,
                        mes=mes,
                        ano=ano,
                        ativo=True
                    )
                    db.add(metrica)
                    db.flush()

                # Vínculos fonte de verdade para este e-mail
                meus_vinculos = vinculos_por_email.get(email, [])
                
                # Mapear histórico existente para reconciliação
                old_history_map = {item.get("projeto_id"): item for item in (metrica.historico_projetos or [])}
                
                # Construir o novo histórico
                novo_historico = []
                p_ids_processados = set()

                for v in meus_vinculos:
                    p_id = str(v.pipefy_id_projeto)
                    p_ids_processados.add(p_id)
                    
                    old_item = old_history_map.get(p_id)
                    
                    # 1. Determinar data_inicio
                    if old_item and old_item.get("data_inicio"):
                        v_inicio = date.fromisoformat(old_item["data_inicio"])
                    else:
                        v_inicio_dt = v.created_at if v.created_at else date.today()
                        v_inicio = v_inicio_dt.date() if isinstance(v_inicio_dt, datetime) else v_inicio_dt
                        
                        if mes == 3 and ano == 2026:
                            v_inicio = max(v_inicio, data_inicio_baseline)
                        else:
                            v_inicio = max(v_inicio, data_inicio_ref)

                    # Regra do Proporcional:
                    # Se está ativo, mostramos o fee completo.
                    # Se está inativo (Churn no mês), calculamos proporcional.
                    if v.active != False:
                        v_valor_prop = v.fee_projeto or 0
                        v_fim = None
                    else:
                        v_fim = v.inactivated_at
                        v_valor_prop = ProjetoParticipacaoService.calcular_valor_proporcional(
                            v.fee_projeto or 0, v_inicio, v_fim, mes, ano
                        )


                    item = {
                        "projeto_id": p_id,
                        "fee_projeto": float(v.fee_projeto) if v.fee_projeto is not None else 0.0,
                        "moeda": moedas_map.get(v.pipefy_id_projeto, "BRL"),
                        "valor_proporcional": float(v_valor_prop),
                        "mes_referencia": f"{ano}-{mes:02d}",
                        "total_dias_mes": total_dias_mes,
                        "data_inicio": v_inicio.isoformat(),
                        "data_fim": v_fim.isoformat() if v_fim else None,
                        "ativo": v.active != False
                    }

                    novo_historico.append(item)

                hoje = date.today()
                for p_id, old_item in old_history_map.items():
                    if p_id not in p_ids_processados:
                        # O projeto não existe mais em InvestidorProjeto (removido via UI)
                        if old_item.get("ativo"):
                            # Estava ativo, agora desativa e define data_fim
                            old_item["ativo"] = False
                            
                            # Se a remoção aconteceu no mês sincronizado, definimos como HOJE
                            if ano == hoje.year and mes == hoje.month:
                                old_item["data_fim"] = hoje.isoformat()
                            else:
                                if not old_item.get("data_fim"):
                                    old_item["data_fim"] = date(ano, mes, total_dias_mes).isoformat()
                            
                            # Recalcular proporcional com o fim da participação
                            d_inicio = date.fromisoformat(old_item["data_inicio"])
                            d_fim = date.fromisoformat(old_item["data_fim"])
                            new_val = ProjetoParticipacaoService.calcular_valor_proporcional(
                                old_item.get("fee_projeto", 0), d_inicio, d_fim, mes, ano
                            )
                            old_item["valor_proporcional"] = float(new_val)
                            novo_historico.append(old_item)
                        else:
                            # Já estava inativo, apenas mantém no histórico deste mês
                            novo_historico.append(old_item)

                
                # Atualizar a métrica (JSONB Mutation)
                metrica.historico_projetos = novo_historico
                flag_modified(metrica, "historico_projetos")



            db.commit()

            # 3. Preencher fixo_mrr_entrega e fixo_mrr_projeto_total com o valor proporcional
            #    convertido USD→BRL a partir do historico_projetos.
            #
            #    IMPORTANTE: fixo_mrr_atual NÃO é atualizado aqui porque ele é o denominador
            #    de todas as colunas GENERATED (calc_churn_real_percentual, calc_delta_csp, etc.).
            #    Atualizar fixo_mrr_atual com um valor proporcional baixo (ex: 167.59) quando
            #    fixo_churn_atual é alto (ex: 6000) causaria overflow em NUMERIC(8,7)
            #    (ex: 6000 / 167.59 = 35.8 > 9.9999999).
            rate_usd = CurrencyService.get_usd_to_brl_rate()

            metricas = db.query(MetricaMensal).filter_by(mes=mes, ano=ano).all()
            for m in metricas:
                total_proporcional_brl = Decimal("0.00")
                if m.historico_projetos:
                    for item in m.historico_projetos:
                        valor = Decimal(str(item.get("valor_proporcional") or 0))
                        m_code = str(item.get("moeda", "BRL")).strip().upper()
                        if m_code == "USD":
                            valor = valor * rate_usd
                        total_proporcional_brl += valor

                # Arredonda para 2 casas decimais antes de gravar (ex: 167.5945712 → 167.59)
                total_proporcional_brl = total_proporcional_brl.quantize(Decimal("0.01"))

                # Apenas fixo_mrr_entrega e fixo_mrr_projeto_total — não afetam as colunas GENERATED
                m.fixo_mrr_entrega = total_proporcional_brl
                m.fixo_mrr_projeto_total = total_proporcional_brl
                db.flush()

            db.commit()
            return True
