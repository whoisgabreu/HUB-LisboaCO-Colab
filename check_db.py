
from database import Session
from models import MonthlyDelivery, Investidor, InvestidorProjeto
from sqlalchemy import text

print("--- Check DB State ---")
with Session() as db:
    count_deliveries = db.query(MonthlyDelivery).count()
    print(f"Total MonthlyDeliveries: {count_deliveries}")
    
    # Check if there are any for March 2026
    m_count = db.query(MonthlyDelivery).filter_by(month=3, year=2026).count()
    print(f"March 2026 Deliveries: {m_count}")
    
    # Check current projects for accounts
    invs = db.query(Investidor).all()
    print(f"Total Users: {len(invs)}")
    # for i in invs:
    #     print(f"  - {i.email} ({i.funcao})")
