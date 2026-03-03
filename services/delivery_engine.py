"""
services/delivery_engine.py
============================
Motor de automação de entregas mensais.
Responsável por:
  - Verificar gatilhos por cargo (Account ou Gestor de Tráfego)
  - Completar entregas na tabela monthly_deliveries de forma idempotente
  - Recalcular MRR na MetricaMensal após conclusão de entrega

Regra financeira:
    MRR_trabalhado(user, client, month) = (entregas_concluidas / 4) * fee_contribuicao

Isolamento garantido por: email + client_id + role + delivery_type + month + year
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import extract

from database import Session
from models import (
    MonthlyDelivery, Investidor, InvestidorProjeto,
    OperacaoCheckin, OperacaoPlanoMidia, OperacaoOtimizacao,
    OperacaoTarefa, MetricaMensal, ProjetoAtivo
)

# ──────────────────────────────────────────────────────────────────────────────
# DEFINIÇÃO DE ENTREGAS POR CARGO
# ──────────────────────────────────────────────────────────────────────────────

DELIVERY_TYPES = {
    "Account": [
        "checkin",           # ≥1 checkin registrado no mês vigente
        "relatorio_account", # ≥1 tarefa quarter concluída no mês
        "planner_monday",    # ≥4 tarefas semanais registradas no mês
        "forecasting",       # ≥1 tarefa quarter registrada no mês (qualquer tipo)
    ],
    "Gestor de Tráfego": [
        "plano_midia",       # ≥1 OperacaoPlanoMidia salvo no mês/ano
        "otimizacao",        # ≥1 OperacaoOtimizacao registrada no mês/ano
        "relatorio_gt",      # ≥1 tarefa quarter concluída no mês
        "config_conta",      # ≥4 tarefas semanais registradas no mês
    ]
}

DELIVERY_LABELS = {
    # Account
    "checkin": "Check-in Semanal",
    "relatorio_account": "Relatório Mensal do Account",
    "planner_monday": "Planner Monday Semanal",
    "forecasting": "Atualização do Forecasting com Metas",
    # Gestor de Tráfego
    "plano_midia": "Plano de Mídia",
    "otimizacao": "Documento de Otimização",
    "relatorio_gt": "Relatório Mensal do Gestor de Tráfego",
    "config_conta": "Configurações de Conta",
}


# ──────────────────────────────────────────────────────────────────────────────
# VERIFICAÇÃO DE GATILHOS
# ──────────────────────────────────────────────────────────────────────────────

def _check_trigger(db, delivery_type: str, email: str, pipefy_id: int, mes: int, ano: int) -> bool:
    """Retorna True se o gatilho para o delivery_type foi acionado."""

    if delivery_type == "checkin":
        # ≥1 checkin do usuário neste projeto no mês/ano
        return db.query(OperacaoCheckin).filter(
            OperacaoCheckin.investidor_email == email,
            OperacaoCheckin.projeto_pipefy_id == pipefy_id,
            extract('year', OperacaoCheckin.created_at) == ano,
            extract('month', OperacaoCheckin.created_at) == mes,
        ).count() >= 1

    elif delivery_type in ("relatorio_account", "relatorio_gt"):
        # ≥1 tarefa quarter CONCLUÍDA para este projeto neste mês/ano
        quarter = (mes - 1) // 3 + 1
        ref = f"{ano}-Q{quarter}"
        return db.query(OperacaoTarefa).filter(
            OperacaoTarefa.projeto_pipefy_id == pipefy_id,
            OperacaoTarefa.tipo == 'quarter',
            OperacaoTarefa.referencia == ref,
            OperacaoTarefa.concluida == True,
        ).count() >= 1

    elif delivery_type in ("planner_monday", "config_conta"):
        # ≥4 tarefas semanais registradas para este projeto neste mês
        # (aproximação: semanas do mês pelo ano e referência)
        from sqlalchemy import and_
        # Semanas do mês (aproximação: W01–W53, filtrando pelo ano e mês via created_at)
        return db.query(OperacaoTarefa).filter(
            OperacaoTarefa.projeto_pipefy_id == pipefy_id,
            OperacaoTarefa.tipo == 'semanal',
            OperacaoTarefa.ano == ano,
            extract('month', OperacaoTarefa.created_at) == mes,
        ).count() >= 4

    elif delivery_type == "forecasting":
        # ≥1 tarefa quarter registrada (não precisa estar concluída)
        quarter = (mes - 1) // 3 + 1
        ref = f"{ano}-Q{quarter}"
        return db.query(OperacaoTarefa).filter(
            OperacaoTarefa.projeto_pipefy_id == pipefy_id,
            OperacaoTarefa.tipo == 'quarter',
            OperacaoTarefa.referencia == ref,
        ).count() >= 1

    elif delivery_type == "plano_midia":
        # ≥1 plano de mídia salvo no mês/ano
        return db.query(OperacaoPlanoMidia).filter(
            OperacaoPlanoMidia.investidor_email == email,
            OperacaoPlanoMidia.projeto_pipefy_id == pipefy_id,
            OperacaoPlanoMidia.mes == mes,
            OperacaoPlanoMidia.ano == ano,
        ).count() >= 1

    elif delivery_type == "otimizacao":
        # ≥1 otimização registrada no mês/ano
        return db.query(OperacaoOtimizacao).filter(
            OperacaoOtimizacao.investidor_email == email,
            OperacaoOtimizacao.projeto_pipefy_id == pipefy_id,
            extract('month', OperacaoOtimizacao.data_otimizacao) == mes,
            extract('year', OperacaoOtimizacao.data_otimizacao) == ano,
        ).count() >= 1

    return False


# ──────────────────────────────────────────────────────────────────────────────
# RECÁLCULO DE MRR
# ──────────────────────────────────────────────────────────────────────────────

def _recalculate_mrr_entrega(db, email: str, mes: int, ano: int):
    """Soma as mrr_contribution de todas as entregas completed do usuário no mês e atualiza MetricaMensal."""
    entregas = db.query(MonthlyDelivery).filter(
        MonthlyDelivery.email == email,
        MonthlyDelivery.month == mes,
        MonthlyDelivery.year == ano,
        MonthlyDelivery.status == 'completed',
    ).all()

    total_mrr = sum(Decimal(str(e.mrr_contribution or 0)) for e in entregas)

    metrica = db.query(MetricaMensal).filter_by(
        email_investidor=email, mes=mes, ano=ano
    ).first()

    if metrica:
        metrica.fixo_mrr_entrega = total_mrr


# ──────────────────────────────────────────────────────────────────────────────
# FUNÇÃO PRINCIPAL: PROCESSAR TODOS OS GATILHOS DE UM USUÁRIO+PROJETO
# ──────────────────────────────────────────────────────────────────────────────

def process_deliveries(email: str, pipefy_id: int, mes: int, ano: int):
    """
    Verifica todos os gatilhos para um usuário + projeto + mês e atualiza
    a tabela monthly_deliveries de forma idempotente.
    Protege meses fechados (não recalcula meses anteriores ao corrente).
    """
    print(f"DEBUG: process_deliveries called for {email}, project {pipefy_id}, {mes}/{ano}")
    from datetime import datetime as dt
    now = dt.now()
    # Não recalcular meses fechados
    if ano < now.year or (ano == now.year and mes < now.month):
        print(f"DEBUG: Skipping process_deliveries - closed month: {mes}/{ano}")
        return {"status": "skipped", "reason": "mes_fechado"}

    with Session() as db:
        # Buscar usuário e seu cargo
        investidor = db.query(Investidor).filter(Investidor.email.ilike(email)).first()
        if not investidor:
            print(f"DEBUG: User {email} not found in Investidor table")
            return {"status": "error", "reason": "usuario_nao_encontrado"}

        role = investidor.funcao
        print(f"DEBUG: User role: {role}")
        
        # Mapeamento expandido para testes
        role_map = {
            "Account": "Account",
            "Gestor de Tráfego": "Gestor de Tráfego",
            "Desenvolvedor": "Gestor de Tráfego" # Para testes do Gabriel
        }
        active_role = role_map.get(role, role)
        delivery_types = DELIVERY_TYPES.get(active_role, [])

        if not delivery_types:
            print(f"DEBUG: No delivery types for role {role}")
            return {"status": "skipped", "reason": f"cargo_sem_entregas: {role}"}

        # Buscar vinculo e fee_contribuicao
        vinculo = db.query(InvestidorProjeto).filter_by(
            email_investidor=email,
            pipefy_id_projeto=pipefy_id,
            active=True
        ).first()

        fee = Decimal(str(vinculo.fee_contribuicao or 0)) if vinculo else Decimal("0")
        mrr_por_entrega = fee * Decimal("0.25")

        results = {}
        for dtype in delivery_types:
            triggered = _check_trigger(db, dtype, email, pipefy_id, mes, ano)

            # Upsert idempotente via UNIQUE constraint
            existing = db.query(MonthlyDelivery).filter_by(
                email=email,
                client_id=pipefy_id,
                role=role,
                delivery_type=dtype,
                month=mes,
                year=ano,
            ).first()

            if not existing:
                existing = MonthlyDelivery(
                    user_id=investidor.id,
                    client_id=pipefy_id,
                    email=email,
                    role=role,
                    delivery_type=dtype,
                    month=mes,
                    year=ano,
                    fee_snapshot=fee,
                    created_at=dt.now(),
                )
                db.add(existing)

            new_status = 'completed' if triggered else 'pending'
            if existing.status != new_status:
                existing.status = new_status
                existing.completed_at = dt.now() if triggered else None
                existing.fee_snapshot = fee
                existing.mrr_contribution = mrr_por_entrega if triggered else Decimal("0")

            results[dtype] = new_status

        _recalculate_mrr_entrega(db, email, mes, ano)
        db.commit()

    return {"status": "ok", "role": role, "deliveries": results}


def process_all_deliveries_for_project(pipefy_id: int, mes: int, ano: int):
    """Processa entregas de todos os investidores vinculados a um projeto."""
    with Session() as db:
        vinculos = db.query(InvestidorProjeto).filter_by(
            pipefy_id_projeto=pipefy_id,
            active=True
        ).all()
        emails = [v.email_investidor for v in vinculos]

    for email in emails:
        process_deliveries(email, pipefy_id, mes, ano)
