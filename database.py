from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv
import os

load_dotenv()

# Monta a connection string a partir das variáveis do .env
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = f"postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # Verifica conexão antes de usar
    pool_recycle=300,         # Recicla conexões a cada 5 min
    echo=False                # Mude para True para debug de queries SQL
)

Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass
