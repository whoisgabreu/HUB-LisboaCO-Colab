from sqlalchemy import text, inspect
from database import engine

def migrate():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            print("Adicionando coluna responsavel_projeto em projetos...")
            inspector = inspect(engine)
            cols = [c['name'] for c in inspector.get_columns('projetos', schema='plataforma_geral')]

            if 'responsavel_projeto' not in cols:
                conn.execute(text("ALTER TABLE plataforma_geral.projetos ADD COLUMN responsavel_projeto VARCHAR(50)"))
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