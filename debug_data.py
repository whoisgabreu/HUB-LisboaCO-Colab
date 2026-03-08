
from database import Session
from models import OperacaoPlanoMidia, MonthlyDelivery, Investidor, ProjetoAtivo
from sqlalchemy import text

print("--- Debugging Media Plan and Deliveries ---")
with Session() as db:
    # 1. Find the project ID for 'AKEOS' (from screenshot)
    proj = db.query(ProjetoAtivo).filter(ProjetoAtivo.nome.ilike('%AKEOS%')).first()
    if not proj:
        print("Project 'AKEOS' not found.")
    else:
        pid = proj.pipefy_id
        print(f"Project: {proj.nome} (Pipefy ID: {pid})")
        
        # 2. Check for plans in March 2026
        plans = db.query(OperacaoPlanoMidia).filter_by(projeto_pipefy_id=pid, mes=3, ano=2026).all()
        print(f"Plans found for March 2026: {len(plans)}")
        for p in plans:
            print(f"  - Plan ID: {p.id}, Email: {p.investidor_email}, Channels: {len(p.dados_plano.get('canais', []))}")
            
        # 3. Check for deliveries
        deliveries = db.query(MonthlyDelivery).filter_by(client_id=pid, month=3, year=2026).all()
        print(f"Deliveries found for March 2026: {len(deliveries)}")
        for d in deliveries:
            print(f"  - Delivery: {d.delivery_type}, Email: {d.email}, Role: {d.role}, Status: {d.status}")

    # 4. Check if there are ANY deliveries or plans at all
    total_plans = db.query(OperacaoPlanoMidia).count()
    total_dels = db.query(MonthlyDelivery).count()
    print(f"Total Plans in DB: {total_plans}")
    print(f"Total Deliveries in DB: {total_dels}")
