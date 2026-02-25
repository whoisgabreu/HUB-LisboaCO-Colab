from sqlalchemy import text, inspect
from database import engine

def migrate():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            print("Adicionando coluna fixo_mrr_projeto_total em investidores_metricas_mensais_novo...")
            inspector = inspect(engine)
            cols = [c['name'] for c in inspector.get_columns('investidores_metricas_mensais_novo', schema='plataforma_geral')]
            
            if 'fixo_mrr_projeto_total' not in cols:
                conn.execute(text("ALTER TABLE plataforma_geral.investidores_metricas_mensais_novo ADD COLUMN fixo_mrr_projeto_total DECIMAL(15, 2)"))
                print("Coluna adicionada.")
            else:
                print("Coluna já existe.")

            trans.commit()
            print("Migração concluída.")
        except Exception as e:
            trans.rollback()
            print(f"Erro: {e}")
            raise

if __name__ == "__main__":
    migrate()
