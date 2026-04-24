import sys
import os
sys.path.append(os.getcwd())
from database import Session
from models import MetricaMensal
from app import _recalcular_mrr_por_entregas

with Session() as db:
    m = db.query(MetricaMensal).filter_by(email_investidor='wemerson.barbosa@v4company.com', mes=4, ano=2026).first()
    if m:
        print("Antes:", m.fixo_mrr_atual, m.calc_remuneracao_total)
        _recalcular_mrr_por_entregas(m)
        db.commit()
        db.refresh(m)
        print("Depois:", m.fixo_mrr_atual, m.calc_remuneracao_total)
