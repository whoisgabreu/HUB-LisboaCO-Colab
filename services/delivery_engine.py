from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from users.models import Investidor
from projetos.models import InvestidorProjeto, ProjetoAtivo
from operacao.models import (
    MonthlyDelivery, OperacaoCheckin, OperacaoPlanoMidia, 
    OperacaoOtimizacao, OperacaoTarefa
)
from remuneracao.models import MetricaMensal

DELIVERY_TYPES = {
    "Account": [
        "checkin",
        "relatorio_account",
        "planner_monday",
        "forecasting",
    ],
    "Gestor de Tráfego": [
        "plano_midia",
        "otimizacao",
        "relatorio_gt",
        "config_conta",
    ]
}

DELIVERY_LABELS = {
    "checkin": "Check-in Semanal",
    "relatorio_account": "Relatório Mensal do Account",
    "planner_monday": "Planner Monday Semanal",
    "forecasting": "Atualização do Forecasting com Metas",
    "plano_midia": "Plano de Mídia",
    "otimizacao": "Documento de Otimização",
    "relatorio_gt": "Relatório Mensal do Gestor de Tráfego",
    "config_conta": "Configurações de Conta",
}

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

def _recalculate_mrr_entrega(email: str, mes: int, ano: int):
    entregas = MonthlyDelivery.objects.filter(
        email=email,
        month=mes,
        year=ano,
        status='completed',
    )
    total_mrr = sum(Decimal(str(e.mrr_contribution or 0)) for e in entregas)
    MetricaMensal.objects.filter(email_investidor=email, mes=mes, ano=ano).update(fixo_mrr_entrega=total_mrr)

def process_deliveries(email: str, pipefy_id: int, mes: int, ano: int):
    now = datetime.now()
    if ano < now.year or (ano == now.year and mes < now.month):
        return {"status": "skipped", "reason": "mes_fechado"}

    with transaction.atomic():
        investidor = Investidor.objects.filter(email__iexact=email).first()
        if not investidor:
            return {"status": "error", "reason": "usuario_nao_encontrado"}

        role = investidor.funcao
        role_map = {
            "Account": "Account",
            "Gestor de Tráfego": "Gestor de Tráfego",
            "Desenvolvedor": "Gestor de Tráfego"
        }
        active_role = role_map.get(role, role)
        delivery_types = DELIVERY_TYPES.get(active_role, [])

        if not delivery_types:
            return {"status": "skipped", "reason": f"cargo_sem_entregas: {role}"}

        vinculo = InvestidorProjeto.objects.filter(
            email_investidor=email,
            pipefy_id_projeto=pipefy_id,
            active=True
        ).first()

        fee = Decimal(str(vinculo.fee_contribuicao or 0)) if vinculo else Decimal("0")
        mrr_por_entrega = fee * Decimal("0.25")

        results = {}
        for dtype in delivery_types:
            triggered = _check_trigger(dtype, email, pipefy_id, mes, ano)

            existing, created = MonthlyDelivery.objects.get_or_create(
                email=email,
                client_id=pipefy_id,
                role=role,
                delivery_type=dtype,
                month=mes,
                year=ano,
                defaults={
                    'user_id': investidor.id,
                    'fee_snapshot': fee,
                    'created_at': timezone.now(),
                }
            )

            new_status = 'completed' if triggered else 'pending'
            if existing.status != new_status:
                existing.status = new_status
                existing.completed_at = timezone.now() if triggered else None
                existing.fee_snapshot = fee
                existing.mrr_contribution = mrr_por_entrega if triggered else Decimal("0")
                existing.save()

            results[dtype] = new_status

        _recalculate_mrr_entrega(email, mes, ano)

    return {"status": "ok", "role": role, "deliveries": results}

def process_all_deliveries_for_project(pipefy_id: int, mes: int, ano: int):
    emails = InvestidorProjeto.objects.filter(
        pipefy_id_projeto=pipefy_id,
        active=True
    ).values_list('email_investidor', flat=True)

    for email in emails:
        process_deliveries(email, pipefy_id, mes, ano)
