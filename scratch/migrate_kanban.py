from sqlalchemy import text
from database import engine

def migrate():
    with engine.connect() as conn:
        print("Iniciando migração do Kanban...")
        
        # 1. Criar tabela kanban_config
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS plataforma_geral.kanban_config (
                id SERIAL PRIMARY KEY,
                slug VARCHAR(100) UNIQUE NOT NULL,
                configuracao JSONB NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("Tabela kanban_config verificada/criada.")

        # 2. Criar tabela kanban_historico
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS plataforma_geral.kanban_historico (
                id SERIAL PRIMARY KEY,
                projeto_id INTEGER NOT NULL,
                data_evento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario_email VARCHAR(255),
                snapshot JSONB NOT NULL
            );
        """))
        print("Tabela kanban_historico verificada/criada.")

        # 3. Adicionar coluna kanban_dados em projetos
        # Verificamos se a coluna já existe antes de tentar adicionar
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'plataforma_geral' 
              AND table_name = 'projetos' 
              AND column_name = 'kanban_dados';
        """))
        
        if not result.fetchone():
            conn.execute(text("ALTER TABLE plataforma_geral.projetos ADD COLUMN kanban_dados JSONB;"))
            print("Coluna kanban_dados adicionada à tabela projetos.")
        else:
            print("Coluna kanban_dados já existe na tabela projetos.")
            
        conn.commit()
        print("Migração concluída com sucesso!")

if __name__ == "__main__":
    migrate()
