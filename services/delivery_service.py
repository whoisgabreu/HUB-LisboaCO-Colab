"""
services/delivery_service.py
============================
Serviço centralizado para gestão de entregas mensais (E4).
Implementa a lógica solicitada de forma aditiva e isolada.
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import extract
from database import Session
from models import (
    MonthlyDelivery, Investidor, InvestidorProjeto,
    OperacaoCheckin, OperacaoPlanoMidia, OperacaoOtimizacao,
    OperacaoTarefa, MetricaMensal
)

class DeliveryService:
    # Definição de Enums (como sugerido para validação no código)
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
        E5: Implementa proteção de meses fechados e recálculo automático.
        """
        # Proteção de Meses Fechados (E5)
        now = datetime.now()
        if year < now.year or (year == now.year and month < now.month):
            return {"status": "skipped", "message": "Não é permitido recalcular meses fechados."}

        if delivery_type not in DeliveryService.DELIVERY_TYPES:
            return {"status": "error", "message": f"Tipo de entrega inválido: {delivery_type}"}

        with Session() as db:
            # 1. Buscar Investidor para obter role e ID
            investidor = db.query(Investidor).filter(Investidor.email.ilike(email)).first()
            if not investidor:
                return {"status": "error", "message": "Usuário não encontrado."}

            role = investidor.funcao
            if not role or role not in DeliveryService.ROLES:
                # Mapeamento de fallback para desenvolvedores/gerência testarem
                if role == "Desenvolvedor":
                    role = "Gestor de Tráfego"
                else:
                    return {"status": "skipped", "message": f"Cargo {role} não possui entregas automáticas."}

            # 2. Verificar se a entrega pertence ao cargo (Isolamento)
            account_types = ['checkin', 'relatorio_account', 'planner_monday', 'forecasting']
            gt_types = ['plano_midia', 'otimizacao', 'relatorio_gt', 'config_conta']
            
            if role == 'Account' and delivery_type not in account_types:
                return {"status": "skipped", "message": f"Entrega {delivery_type} não pertence ao cargo Account."}
            if role == 'Gestor de Tráfego' and delivery_type not in gt_types:
                return {"status": "skipped", "message": f"Entrega {delivery_type} não pertence ao cargo Gestor de Tráfego."}

            # 3. Buscar vínculo para obter o fee_contribuicao (snapshot)
            vinculo = db.query(InvestidorProjeto).filter_by(
                email_investidor=email,
                pipefy_id_projeto=client_id,
                active=True
            ).first()
            
            # Use fee_contribuicao se existir e > 0, senão cai para fee_projeto
            fee_base = Decimal("0")
            if vinculo:
                # Achar a moeda do projeto
                from models import ProjetoAtivo, ProjetoOnetime
                proj_ativo = db.query(ProjetoAtivo).filter_by(pipefy_id=client_id).first()
                if not proj_ativo:
                    proj_ativo = db.query(ProjetoOnetime).filter_by(pipefy_id=client_id).first()
                
                moeda = proj_ativo.moeda if proj_ativo else "BRL"

                fee_contri = Decimal(str(vinculo.fee_contribuicao or 0))
                fee_proj = Decimal(str(vinculo.fee_projeto or 0))
                fee_base = fee_contri if fee_contri > 0 else fee_proj
                
                # Conversão
                if moeda == "USD":
                    from services.currency import CurrencyService
                    rate = CurrencyService.get_usd_to_brl_rate()
                    fee_base *= rate

                if vinculo.cientista:
                    fee_base *= Decimal("1.5")

            # 4. Verificar Gatilho (Trigger)
            triggered = DeliveryService._check_trigger(db, delivery_type, email, client_id, month, year)

            # 5. Upsert Idempotente
            delivery = db.query(MonthlyDelivery).filter_by(
                email=email,
                client_id=client_id,
                role=role,
                delivery_type=delivery_type,
                month=month,
                year=year
            ).first()

            if not delivery:
                delivery = MonthlyDelivery(
                    user_id=investidor.id,
                    client_id=client_id,
                    email=email,
                    role=role,
                    delivery_type=delivery_type,
                    month=month,
                    year=year,
                    status='pending',
                    created_at=datetime.now()
                )
                db.add(delivery)

            # Atualizar status se mudou
            new_status = 'completed' if triggered else 'pending'
            if delivery.status != new_status:
                delivery.status = new_status
                delivery.completed_at = datetime.now() if triggered else None
                delivery.fee_snapshot = fee_base
            
            db.commit()
            
            # 6. Recalcular MRR do vínculo (E5: Fórmula consolidada por role/client/user/month)
            DeliveryService._recalculate_mrr_worked(db, investidor.id, client_id, role, month, year, fee_base)
            db.commit()

            # 7. Sincronizar MRR total na MetricaMensal
            DeliveryService._sync_metrica_mrr(db, email, month, year)
            db.commit()

        return {"status": "ok", "delivery_status": new_status}

    @staticmethod
    def _recalculate_mrr_worked(db, user_id, client_id, role, month, year, fee_base):
        """
        E5: Implementa a nova fórmula: MRR Trabalhado = (Entregas Completas / 4) * Fee.
        Atualiza mrr_contribution em TODAS as entregas deste vínculo no mês para manter coerência.
        """
        # Buscar todas as entregas deste vínculo no mês
        entregas = db.query(MonthlyDelivery).filter_by(
            user_id=user_id,
            client_id=client_id,
            role=role,
            month=month,
            year=year
        ).all()

        completed_count = sum(1 for e in entregas if e.status == 'completed')
        
        # O MRR Trabalhado do vínculo é proporcional
        mrr_total_vinculo = (Decimal(completed_count) / Decimal("4")) * fee_base
        
        # Para refletir isso na MetricaMensal via soma, distribuímos ou atribuímos o valor total.
        # A regra diz que a soma das contribuições deve ser o MRR. 
        # Como o recalcular_mrr_entrega soma MonthlyDelivery.mrr_contribution, 
        # vamos dividir o total pelo número de entregas concluídas ou atribuir de forma que a soma bata.
        # Decisão: Cada entrega 'completed' recebe (1/4) * Fee. As 'pending' recebem 0.
        mrr_por_entrega = fee_base / Decimal("4")

        for e in entregas:
            if e.status == 'completed':
                e.mrr_contribution = mrr_por_entrega
            else:
                e.mrr_contribution = Decimal("0")

        return {"status": "ok"}

    @staticmethod
    def _check_trigger(db, delivery_type: str, email: str, pipefy_id: int, mes: int, ano: int) -> bool:
        """Lógica de gatilhos importada e adaptada do delivery_engine."""
        if delivery_type == "checkin":
            return db.query(OperacaoCheckin).filter(
                OperacaoCheckin.investidor_email == email,
                OperacaoCheckin.projeto_pipefy_id == pipefy_id,
                extract('year', OperacaoCheckin.created_at) == ano,
                extract('month', OperacaoCheckin.created_at) == mes,
            ).count() >= 1

        elif delivery_type in ("relatorio_account", "relatorio_gt"):
            quarter = (mes - 1) // 3 + 1
            ref = f"{ano}-Q{quarter}"
            return db.query(OperacaoTarefa).filter(
                OperacaoTarefa.projeto_pipefy_id == pipefy_id,
                OperacaoTarefa.tipo == 'quarter',
                OperacaoTarefa.referencia == ref,
                OperacaoTarefa.concluida == True,
            ).count() >= 1

        elif delivery_type in ("planner_monday", "config_conta"):
            from datetime import datetime
            tarefas = db.query(OperacaoTarefa).filter(
                OperacaoTarefa.projeto_pipefy_id == pipefy_id,
                OperacaoTarefa.tipo == 'semanal',
                OperacaoTarefa.ano == ano,
            ).all()
            
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
            return db.query(OperacaoTarefa).filter(
                OperacaoTarefa.projeto_pipefy_id == pipefy_id,
                OperacaoTarefa.tipo == 'quarter',
                OperacaoTarefa.referencia == ref,
            ).count() >= 1

        elif delivery_type == "plano_midia":
            return db.query(OperacaoPlanoMidia).filter(
                OperacaoPlanoMidia.investidor_email == email,
                OperacaoPlanoMidia.projeto_pipefy_id == pipefy_id,
                OperacaoPlanoMidia.mes == mes,
                OperacaoPlanoMidia.ano == ano,
            ).count() >= 1

        elif delivery_type == "otimizacao":
            return db.query(OperacaoOtimizacao).filter(
                OperacaoOtimizacao.investidor_email == email,
                OperacaoOtimizacao.projeto_pipefy_id == pipefy_id,
                extract('month', OperacaoOtimizacao.data_otimizacao) == mes,
                extract('year', OperacaoOtimizacao.data_otimizacao) == ano,
            ).count() >= 1

        return False

    @staticmethod
    def _sync_metrica_mrr(db, email: str, mes: int, ano: int):
        """Sincroniza o fixo_mrr_entrega na MetricaMensal após alteração nas entregas."""
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
            metrica.fixo_mrr_atual = total_mrr
            metrica.fixo_mrr_entrega = total_mrr
