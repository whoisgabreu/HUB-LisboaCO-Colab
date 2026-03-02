from sqlalchemy import text
from database import engine

with engine.connect() as conn:
    print("Iniciando migração da tabela operacao_checkins...")
    try:
        conn.execute(text("ALTER TABLE plataforma_geral.operacao_checkins ADD COLUMN campanhas_ativas BOOLEAN DEFAULT TRUE;"))
        print("Coluna campanhas_ativas adicionada.")
    except Exception as e:
        print("Aviso (campanhas_ativas):", e)

    try:
        conn.execute(text("ALTER TABLE plataforma_geral.operacao_checkins ADD COLUMN gap_comunicacao BOOLEAN DEFAULT FALSE;"))
        print("Coluna gap_comunicacao adicionada.")
    except Exception as e:
        print("Aviso (gap_comunicacao):", e)

    try:
        conn.execute(text("ALTER TABLE plataforma_geral.operacao_checkins ADD COLUMN cliente_reclamou BOOLEAN DEFAULT FALSE;"))
        print("Coluna cliente_reclamou adicionada.")
    except Exception as e:
        print("Aviso (cliente_reclamou):", e)

    conn.commit()
    print("Migração concluída.")
