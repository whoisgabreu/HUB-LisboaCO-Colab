
import os
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = f"postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
engine = create_engine(DATABASE_URL)

def inspect_db():
    inspector = inspect(engine)
    schema = "plataforma_geral"
    tables = inspector.get_table_names(schema=schema)
    print(f"Tables in schema '{schema}':")
    for table in tables:
        print(f" - {table}")
        
    target_tables = ["projetos_ativos", "projetos_inativos", "projetos_onetime", "projeto"]
    for table in target_tables:
        if table in tables:
            print(f"\nStructure of '{table}':")
            columns = inspector.get_columns(table, schema=schema)
            for column in columns:
                print(f"  {column['name']}: {column['type']}")
        else:
            print(f"\nTable '{table}' NOT FOUND in schema '{schema}'.")

if __name__ == "__main__":
    inspect_db()
