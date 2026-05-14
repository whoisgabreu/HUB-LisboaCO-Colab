
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
    
    table_name = "projetos" # Checking 'projetos' since 'projeto' wasn't found
    if table_name in tables:
        print(f"\nStructure of '{table_name}':")
        columns = inspector.get_columns(table_name, schema=schema)
        for column in columns:
            print(f"  {column['name']}: {column['type']}")
    else:
        print(f"\nTable '{table_name}' NOT FOUND in schema '{schema}'.")

if __name__ == "__main__":
    inspect_db()
