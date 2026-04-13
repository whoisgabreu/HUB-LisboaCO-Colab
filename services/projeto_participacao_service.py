import calendar
from decimal import Decimal
from datetime import datetime, date
from collections import defaultdict
from django.db import connection, transaction
from django.db.models import Q
from remuneracao.models import MetricaMensal, RemuneracaoCargo
from projetos.models import InvestidorProjeto, ProjetoAtivo, ProjetoOnetime, ProjetoInativo
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
        inicio_mes = date(ano, mes, 1)
        fim_mes = date(ano, mes, total_dias_mes)
        
        data_fim_calc_val = data_fim if data_fim else fim_mes
        data_inicio_calc = max(data_inicio, inicio_mes)
        data_fim_calc = min(data_fim_calc_val, fim_mes)
        
        if data_inicio_calc > data_fim_calc:
            return Decimal("0.00")
            
        dias_trabalhados = (data_fim_calc - data_inicio_calc).days + 1
        
        fee_decimal = Decimal(str(fee or 0))
        valor_proporcional = (Decimal(dias_trabalhados) * fee_decimal) / Decimal(total_dias_mes)
        
        return valor_proporcional.quantize(Decimal("0.01"))

    @staticmethod
    def sincronizar_remuneracao(mes, ano):
        """
        Sincroniza todos os funcionários para o mês de referência usando investidores_projetos como fonte de verdade.
        Migrado para Django ORM.
        """
        with transaction.atomic():
            data_inicio_ref = date(ano, mes, 1)
            total_dias_mes = ProjetoParticipacaoService.get_total_days_in_month(mes, ano)
            data_fim_ref = date(ano, mes, total_dias_mes)
            data_inicio_baseline = date(2026, 3, 1)

            # 2. Buscar vínculos fonte de verdade
            vinculos = InvestidorProjeto.objects.filter(
                Q(active=True) | 
                Q(active__isnull=True) | 
                Q(active=False, inactivated_at__month=mes, inactivated_at__year=ano)
            )

            # 3. Mapear moedas dos projetos
            proj_ids = [v.pipefy_id_projeto for v in vinculos]
            moedas_map = {}
            
            tabelas_projetos = [ProjetoAtivo, ProjetoOnetime, ProjetoInativo]
            for Model in tabelas_projetos:
                projs = Model.objects.filter(pipefy_id__in=proj_ids).values_list('pipefy_id', 'moeda')
                for pid, moeda in projs:
                    if pid not in moedas_map:
                        m_str = str(moeda).strip().upper() if moeda else "BRL"
                        moedas_map[pid] = "USD" if m_str == "USD" else "BRL"

            vinculos_por_email = defaultdict(list)
            for v in vinculos:
                vinculos_por_email[v.email_investidor].append(v)

            metricas_existentes = MetricaMensal.objects.filter(mes=mes, ano=ano)
            emails_com_metrica = {m.email_investidor for m in metricas_existentes}
            todos_emails = set(vinculos_por_email.keys()) | emails_com_metrica

            for email in todos_emails:
                metrica = next((m for m in metricas_existentes if m.email_investidor == email), None)
                if not metrica:
                    metrica = MetricaMensal.objects.create(
                        email_investidor=email,
                        mes=mes,
                        ano=ano,
                        ativo=True
                    )

                meus_vinculos = vinculos_por_email.get(email, [])
                old_history_map = {item.get("projeto_id"): item for item in (metrica.historico_projetos or [])}
                novo_historico = []
                p_ids_processados = set()

                for v in meus_vinculos:
                    p_id = str(v.pipefy_id_projeto)
                    p_ids_processados.add(p_id)
                    
                    old_item = old_history_map.get(p_id)
                    
                    if old_item and old_item.get("data_inicio"):
                        v_inicio = date.fromisoformat(old_item["data_inicio"])
                    else:
                        v_inicio_dt = v.created_at if v.created_at else date.today()
                        v_inicio = v_inicio_dt.date() if isinstance(v_inicio_dt, datetime) else v_inicio_dt
                        if mes == 3 and ano == 2026:
                            v_inicio = max(v_inicio, data_inicio_baseline)
                        else:
                            v_inicio = max(v_inicio, data_inicio_ref)

                    v_fim = None if v.active != False else v.inactivated_at
                    fee_base = Decimal(str(v.fee_projeto or 0))
                    if v.cientista:
                        fee_base *= Decimal("1.5")
                        
                    v_valor_prop = ProjetoParticipacaoService.calcular_valor_proporcional(
                        fee_base, v_inicio, v_fim, mes, ano
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
                        "ativo": v.active != False,
                        "cientista": v.cientista or False
                    }
                    novo_historico.append(item)

                hoje = date.today()
                for p_id, old_item in old_history_map.items():
                    if p_id not in p_ids_processados:
                        if old_item.get("ativo"):
                            old_item["ativo"] = False
                            if ano == hoje.year and mes == hoje.month:
                                old_item["data_fim"] = hoje.isoformat()
                            else:
                                if not old_item.get("data_fim"):
                                    old_item["data_fim"] = date(ano, mes, total_dias_mes).isoformat()
                            
                            d_inicio = date.fromisoformat(old_item["data_inicio"])
                            d_fim = date.fromisoformat(old_item["data_fim"])
                            new_val = ProjetoParticipacaoService.calcular_valor_proporcional(
                                old_item.get("fee_projeto", 0), d_inicio, d_fim, mes, ano
                            )
                            old_item["valor_proporcional"] = float(new_val)
                        novo_historico.append(old_item)

                metrica.historico_projetos = novo_historico
                metrica.save()

            rate_usd = CurrencyService.get_usd_to_brl_rate()
            metricas = MetricaMensal.objects.filter(mes=mes, ano=ano)
            for m in metricas:
                total_proporcional_brl = Decimal("0.00")
                if m.historico_projetos:
                    for item in m.historico_projetos:
                        valor = Decimal(str(item.get("valor_proporcional") or 0))
                        m_code = str(item.get("moeda", "BRL")).strip().upper()
                        if m_code == "USD":
                            valor = valor * rate_usd
                        total_proporcional_brl += valor

                total_proporcional_brl = total_proporcional_brl.quantize(Decimal("0.01"))
                m.fixo_mrr_entrega = total_proporcional_brl
                m.fixo_mrr_projeto_total = total_proporcional_brl
                m.save()

            return True
