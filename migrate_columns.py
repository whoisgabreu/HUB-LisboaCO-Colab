from database import engine
from sqlalchemy import text

sql = "ALTER TABLE plataforma_geral.investidores_metricas_mensais_novo ADD COLUMN IF NOT EXISTS fixo_mrr_entrega DECIMAL(15, 2)"

with engine.connect() as conn:
    print("Executando migração...")
    conn.execute(text(sql))
    conn.commit()
    print("Sucesso: Coluna fixo_mrr_entrega adicionada.")
