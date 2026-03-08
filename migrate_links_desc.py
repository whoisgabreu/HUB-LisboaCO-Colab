from database import engine
from sqlalchemy import text

def migrate():
    print("Iniciando migração: Adicionando coluna 'descricao' em 'operacao_links_uteis'...")
    try:
        with engine.begin() as conn:
            # Lista de colunas para verificar/adicionar
            columns_to_add = [
                ("descricao", "TEXT"),
                ("icone", "VARCHAR(50)"),
                ("criado_por", "TEXT"),
                ("created_at", "TIMESTAMP")
            ]
            
            for col_name, col_type in columns_to_add:
                check_sql = text(f"""
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema = 'plataforma_geral' 
                    AND table_name = 'operacao_links_uteis' 
                    AND column_name = '{col_name}'
                """)
                result = conn.execute(check_sql).fetchone()
                
                if not result:
                    conn.execute(text(f"ALTER TABLE plataforma_geral.operacao_links_uteis ADD COLUMN {col_name} {col_type}"))
                    print(f"Coluna '{col_name}' adicionada com sucesso.")
                else:
                    print(f"Coluna '{col_name}' já existe.")
    except Exception as e:
        print(f"Erro na migração: {e}")

if __name__ == "__main__":
    migrate()
