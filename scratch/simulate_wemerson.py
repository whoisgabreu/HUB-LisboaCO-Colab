import os
import sys
sys.path.append(os.getcwd())
from app import app
from database import Session
from models import MetricaMensal

def analyze():
    with app.app_context():
        with Session() as db:
            m = db.query(MetricaMensal).filter(
                MetricaMensal.email_investidor.ilike('%wemerson%'),
                MetricaMensal.mes == 4,
                MetricaMensal.ano == 2026
            ).first()
            if m:
                print(f"Atual: fixo_mrr_atual={m.fixo_mrr_atual}, calc_remuneracao_total={m.calc_remuneracao_total}")
                print(f"Config: fixa={m.fixo_remuneracao_fixa}, min={m.fixo_remuneracao_minima}, max={m.fixo_remuneracao_maxima}")
                print(f"MRR Config: min={m.fixo_mrr_minimo}, esp={m.fixo_mrr_esperado}, teto={m.fixo_mrr_teto}")
analyze()
