import sys
sys.path.append('.')
from database import Session
from services.remuneracao import calcular_metricas_mensais
from models import MetricaMensal

# Backup metrica original
with Session() as db:
    m = db.query(MetricaMensal).filter_by(email_investidor='wemerson.barbosa@v4company.com', mes=4, ano=2026).first()
    if m:
        print(f"BEFORE: Entregue={m.fixo_mrr_entrega}, Atual={m.fixo_mrr_atual}")

# We will apply the logic locally here to see what it would output
