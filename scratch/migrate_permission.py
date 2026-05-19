from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = f"postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"

engine = create_engine(DATABASE_URL)

def migrate():
    with engine.connect() as conn:
        print("Adicionando coluna pode_editar_kanban...")
        conn.execute(text('ALTER TABLE plataforma_geral.investidores ADD COLUMN IF NOT EXISTS pode_editar_kanban BOOLEAN DEFAULT FALSE'))
        # Para que usuários existentes possam ver/testar, vamos dar permissão para quem já é admin
        conn.execute(text("UPDATE plataforma_geral.investidores SET pode_editar_kanban = TRUE WHERE nivel_acesso IN ('admin', 'master')"))
        conn.commit()
        print("Migração concluída.")

if __name__ == "__main__":
    migrate()
