from database import engine
from sqlalchemy import text
from decimal import Decimal

def inspect():
    with engine.connect() as conn:
        # 1. Metricas
        print("\n--- METRICAS ---")
        q = text("SELECT email_investidor, fixo_mrr_atual, fixo_churn_atual FROM plataforma_geral.investidores_metricas_mensais_novo LIMIT 2")
        res = conn.execute(q).fetchall()
        for r in res:
            print(f"Investidor: {r[0]} | MRR: {r[1]} | Churn: {r[2]}")
            
        # 2. Projetos
        print("\n--- PROJETOS ATIVOS ---")
        q = text("SELECT nome, fee FROM plataforma_geral.projetos_ativos LIMIT 2")
        res = conn.execute(q).fetchall()
        for r in res:
            print(f"Projeto: {r[0]} | Fee: {r[1]}")

        # 3. Cargos
        print("\n--- CARGOS ---")
        q = text("SELECT fixo_cargo, fixo_ticket_medio, fixo_mrr_esperado FROM plataforma_geral.remuneracao_cargos LIMIT 1")
        res = conn.execute(q).fetchall()
        for r in res:
            print(f"Cargo: {r[0]} | TM: {r[1]} | MRR Esp: {r[2]}")

if __name__ == "__main__":
    inspect()
