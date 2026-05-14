
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = f"postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
engine = create_engine(DATABASE_URL)

def verify():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT * FROM plataforma_geral.projetos WHERE pipefy_id = 1313907605")).fetchone()
        if res:
            print(dict(res._mapping))
        else:
            print("Project not found")

if __name__ == "__main__":
    verify()
