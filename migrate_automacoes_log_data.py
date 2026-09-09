from sqlalchemy import text, inspect
from database import engine

def migrate():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            print("Configurando DEFAULT em automacoes_log.executed_at...")
            inspector = inspect(engine)
            cols = {c['name']: c for c in inspector.get_columns('automacoes_log', schema='plataforma_geral')}

            if 'executed_at' not in cols:
                print("Coluna executed_at não existe; nada a fazer.")
            else:
                default = cols['executed_at'].get('default')
                conn.execute(text(
                    "ALTER TABLE plataforma_geral.automacoes_log "
                    "ALTER COLUMN executed_at SET DEFAULT (now() AT TIME ZONE 'America/Sao_Paulo')"
                ))
                print("DEFAULT aplicado.")

            trans.commit()
            print("Migração concluída.")
        except Exception as e:
            trans.rollback()
            print(f"Erro: {e}")
            raise

if __name__ == "__main__":
    migrate()