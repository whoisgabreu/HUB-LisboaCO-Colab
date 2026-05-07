
from database import Session
from models import Investidor, InvestidorProjeto, MetricaMensal
from decimal import Decimal

def investigate_churn():
    with Session() as db:
        inv = db.query(Investidor).filter(Investidor.email == "wemerson.barbosa@v4company.com").first()
        if not inv:
            print("Investidor não encontrado.")
            return

        print(f"Investidor: {inv.nome} ({inv.email})")

        # Check MetricaMensal for April 2026
        metrica = db.query(MetricaMensal).filter(
            MetricaMensal.email_investidor == inv.email,
            MetricaMensal.mes == 4,
            MetricaMensal.ano == 2026
        ).first()

        if metrica:
            print(f"Métrica Abril 2026: Churn Atual = {metrica.fixo_churn_atual}")
            print(f"Detalhes na métrica: {metrica.detalhes}")
        else:
            print("Métrica de Abril 2026 não encontrada.")

        # Check projects for this investor
        vinculos = db.query(InvestidorProjeto).filter(
            InvestidorProjeto.email_investidor == inv.email
        ).all()

        print(f"\nVínculos encontrados: {len(vinculos)}")
        for v in vinculos:
            status = "Ativo" if v.active else f"Inativo (em {v.inactivated_at})"
            print(f"Projeto: {v.nome_projeto} (ID: {v.pipefy_id_projeto})")
            print(f"  Status: {status}")
            print(f"  Fee: {v.fee_projeto}")
            print(f"  Cientista: {v.cientista}")

            if v.inactivated_at and v.inactivated_at.strftime("%Y-%m") == "2026-04":
                 print(f"  *** ESTE PROJETO CONTABILIZA CHURN EM ABRIL 2026 ***")

if __name__ == "__main__":
    investigate_churn()
