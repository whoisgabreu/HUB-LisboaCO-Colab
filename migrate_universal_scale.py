from sqlalchemy import text, inspect
from database import engine, Session
from decimal import Decimal

def migrate():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            print("--- Iniciando Migração de Escala e Centralização ---")

            # 1. Adicionar novas colunas em investidores_projetos
            print("Adicionando colunas em investidores_projetos...")
            inspector = inspect(engine)
            cols = [c['name'] for c in inspector.get_columns('investidores_projetos', schema='plataforma_geral')]
            
            if 'nome_projeto' not in cols:
                conn.execute(text("ALTER TABLE plataforma_geral.investidores_projetos ADD COLUMN nome_projeto VARCHAR(250)"))
            if 'fee_projeto' not in cols:
                conn.execute(text("ALTER TABLE plataforma_geral.investidores_projetos ADD COLUMN fee_projeto DECIMAL(15, 2)"))
            if 'fee_contribuicao' not in cols:
                conn.execute(text("ALTER TABLE plataforma_geral.investidores_projetos ADD COLUMN fee_contribuicao DECIMAL(15, 2)"))

            # 2. Converter valores nas tabelas de projetos (Centavos -> Unidades)
            for table in ['projetos_ativos', 'projetos_onetime', 'projetos_inativos']:
                print(f"Convertendo fees na tabela {table}...")
                # Primeiro alteramos o tipo para DECIMAL se for Integer, ou apenas dividimos
                # Como vi que 'fee' em projetos_ativos era 675647 (Integer no SQLAlchemy ou BigInt/Int no PG)
                # Vamos converter para Decimal e dividir por 100
                conn.execute(text(f"ALTER TABLE plataforma_geral.{table} ALTER COLUMN fee TYPE DECIMAL(15, 2) USING (fee::numeric / 100.0)"))

            # 3. Converter valores na tabela de operações
            print("Convertendo valores na tabela operacao_entregas_mensais...")
            conn.execute(text("ALTER TABLE plataforma_geral.operacao_entregas_mensais ALTER COLUMN valor_fee_original TYPE DECIMAL(15, 2) USING (valor_fee_original::numeric / 100.0)"))
            conn.execute(text("ALTER TABLE plataforma_geral.operacao_entregas_mensais ALTER COLUMN valor_contribuicao_mrr TYPE DECIMAL(15, 2) USING (valor_contribuicao_mrr::numeric / 100.0)"))

            # 4. Popular as novas colunas em investidores_projetos
            print("Populando novas colunas em investidores_projetos...")
            # Busco dados das tabelas de projetos e atualizo investidores_projetos
            # Nota: usamos projetos_ativos como fonte principal, depois onetime e inativos
            
            # Subqueries para atualizar
            update_sql = """
            UPDATE plataforma_geral.investidores_projetos ip
            SET 
                nome_projeto = p.nome,
                fee_projeto = p.fee,
                fee_contribuicao = p.fee
            FROM (
                SELECT pipefy_id, nome, fee FROM plataforma_geral.projetos_ativos
                UNION ALL
                SELECT pipefy_id, nome, fee FROM plataforma_geral.projetos_onetime
                UNION ALL
                SELECT pipefy_id, nome, fee FROM plataforma_geral.projetos_inativos
            ) p
            WHERE ip.pipefy_id_projeto = p.pipefy_id;
            """
            conn.execute(text(update_sql))

            trans.commit()
            print("--- Migração concluída com sucesso! ---")
        except Exception as e:
            trans.rollback()
            print(f"ERRO NA MIGRAÇÃO: {e}")
            raise

if __name__ == "__main__":
    migrate()
