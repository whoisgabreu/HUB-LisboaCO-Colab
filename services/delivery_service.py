from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from users.models import Investidor
from projetos.models import InvestidorProjeto, ProjetoAtivo, ProjetoOnetime
from operacao.models import (
    MonthlyDelivery, OperacaoCheckin, OperacaoPlanoMidia,
    OperacaoOtimizacao, OperacaoTarefa
)
from remuneracao.models import MetricaMensal
from .currency import CurrencyService

class DeliveryService:
    ROLES = ['Account', 'Gestor de Tráfego']
    STATUS = ['pending', 'completed']
    DELIVERY_TYPES = [
        'checkin', 'relatorio_account', 'planner_monday', 'forecasting',
        'plano_midia', 'otimizacao', 'relatorio_gt', 'config_conta'
    ]

    @staticmethod
    def checkAndComplete(email: str, client_id: int, delivery_type: str, month: int, year: int):
        """
        Verifica se uma entrega específica deve ser marcada como concluída.
        Migrado para Django ORM.
        """
        now = datetime.now()
        if year < now.year or (year == now.year and month < now.month):
            return {"status": "skipped", "message": "Não é permitido recalcular meses fechados."}

        if delivery_type not in DeliveryService.DELIVERY_TYPES:
            return {"status": "error", "message": f"Tipo de entrega inválido: {delivery_type}"}

        with transaction.atomic():
            investidor = Investidor.objects.filter(email__iexact=email).first()
            if not investidor:
                return {"status": "error", "message": "Usuário não encontrado."}

            role = investidor.funcao
            if not role or role not in DeliveryService.ROLES:
                if role == "Desenvolvedor":
                    role = "Gestor de Tráfego"
                else:
                    return {"status": "skipped", "message": f"Cargo {role} não possui entregas automáticas."}

            account_types = ['checkin', 'relatorio_account', 'planner_monday', 'forecasting']
            gt_types = ['plano_midia', 'otimizacao', 'relatorio_gt', 'config_conta']
            
            if role == 'Account' and delivery_type not in account_types:
                return {"status": "skipped", "message": f"Entrega {delivery_type} não pertence ao cargo Account."}
            if role == 'Gestor de Tráfego' and delivery_type not in gt_types:
                return {"status": "skipped", "message": f"Entrega {delivery_type} não pertence ao cargo Gestor de Tráfego."}

            vinculo = InvestidorProjeto.objects.filter(
                email_investidor=email,
                pipefy_id_projeto=client_id,
                active=True
            ).first()
            
            fee_base = Decimal("0")
            if vinculo:
                proj = ProjetoAtivo.objects.filter(pipefy_id=client_id).first()
                if not proj:
                    proj = ProjetoOnetime.objects.filter(pipefy_id=client_id).first()
                
                moeda = proj.moeda if proj else "BRL"
                fee_contri = Decimal(str(vinculo.fee_contribuicao or 0))
                fee_proj = Decimal(str(vinculo.fee_projeto or 0))
                fee_base = fee_contri if fee_contri > 0 else fee_proj
                
                if moeda == "USD":
                    rate = CurrencyService.get_usd_to_brl_rate()
                    fee_base *= rate

                if vinculo.cientista:
                    fee_base *= Decimal("1.5")

            triggered = DeliveryService._check_trigger(delivery_type, email, client_id, month, year)

            delivery, created = MonthlyDelivery.objects.get_or_create(
                email=email,
                client_id=client_id,
                role=role,
                delivery_type=delivery_type,
                month=month,
                year=year,
                defaults={
                    'user_id': investidor.id,
                    'status': 'pending',
                    'created_at': datetime.now()
                }
            )

            new_status = 'completed' if triggered else 'pending'
            if delivery.status != new_status:
                delivery.status = new_status
                delivery.completed_at = datetime.now() if triggered else None
                delivery.fee_snapshot = fee_base
                delivery.save()
            
            DeliveryService._recalculate_mrr_worked(investidor.id, client_id, role, month, year, fee_base)
            DeliveryService._sync_metrica_mrr(email, month, year)

        return {"status": "ok", "delivery_status": new_status}

    @staticmethod
    def _recalculate_mrr_worked(user_id, client_id, role, month, year, fee_base):
        entregas = MonthlyDelivery.objects.filter(
            user_id=user_id,
            client_id=client_id,
            role=role,
            month=month,
            year=year
        )

        completed_count = sum(1 for e in entregas if e.status == 'completed')
        mrr_por_entrega = fee_base / Decimal("4")

        for e in entregas:
            if e.status == 'completed':
                e.mrr_contribution = mrr_por_entrega
            else:
                e.mrr_contribution = Decimal("0")
            e.save()

        return {"status": "ok"}

    @staticmethod
    def _check_trigger(delivery_type: str, email: str, pipefy_id: int, mes: int, ano: int) -> bool:
        if delivery_type == "checkin":
            return OperacaoCheckin.objects.filter(
                investidor_email=email,
                projeto_pipefy_id=pipefy_id,
                created_at__year=ano,
                created_at__month=mes,
            ).count() >= 1

        elif delivery_type in ("relatorio_account", "relatorio_gt"):
            quarter = (mes - 1) // 3 + 1
            ref = f"{ano}-Q{quarter}"
            return OperacaoTarefa.objects.filter(
                projeto_pipefy_id=pipefy_id,
                tipo='quarter',
                referencia=ref,
                concluida=True,
            ).count() >= 1

        elif delivery_type in ("planner_monday", "config_conta"):
            tarefas = OperacaoTarefa.objects.filter(
                projeto_pipefy_id=pipefy_id,
                tipo='semanal',
                ano=ano,
            )
            count = 0
            for t in tarefas:
                try:
                    if t.referencia and '-W' in t.referencia:
                        y, w = map(int, t.referencia.split('-W'))
                        d = datetime.fromisocalendar(y, w, 1)
                        if d.month == mes:
                            count += 1
                except Exception:
                    pass
            return count >= 4

        elif delivery_type == "forecasting":
            quarter = (mes - 1) // 3 + 1
            ref = f"{ano}-Q{quarter}"
            return OperacaoTarefa.objects.filter(
                projeto_pipefy_id=pipefy_id,
                tipo='quarter',
                referencia=ref,
            ).count() >= 1

        elif delivery_type == "plano_midia":
            return OperacaoPlanoMidia.objects.filter(
                investidor_email=email,
                projeto_pipefy_id=pipefy_id,
                mes=mes,
                ano=ano,
            ).count() >= 1

        elif delivery_type == "otimizacao":
            return OperacaoOtimizacao.objects.filter(
                investidor_email=email,
                projeto_pipefy_id=pipefy_id,
                data_otimizacao__month=mes,
                data_otimizacao__year=ano,
            ).count() >= 1

        return False

    @staticmethod
    def _sync_metrica_mrr(email: str, mes: int, ano: int):
        entregas = MonthlyDelivery.objects.filter(
            email=email,
            month=mes,
            year=ano,
            status='completed',
        )
        total_mrr = sum(Decimal(str(e.mrr_contribution or 0)) for e in entregas)
        MetricaMensal.objects.filter(email_investidor=email, mes=mes, ano=ano).update(
            fixo_mrr_atual=total_mrr,
            fixo_mrr_entrega=total_mrr
        )
