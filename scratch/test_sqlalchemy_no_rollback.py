from database import Session
from models import Investidor
from sqlalchemy import text

def test_rollback():
    with Session() as db:
        # 1. Faça uma alteração real na sessão
        inv = db.query(Investidor).first()
        old_name = inv.nome
        inv.nome = old_name + " TEST"
        db.flush()
        
        # 2. Crie um savepoint (sem with)
        try:
            nested = db.begin_nested()
            db.execute(text("SELECT COUNT(*) FROM plataforma_geral.tabela_que_nao_existe")).scalar()
            nested.commit()
        except Exception as e:
            # Nada aqui (como eu tinha deixado no app.py)
            pass
        
        # 3. Tente fazer commit
        try:
            db.commit()
            print("Commit com sucesso sem rollback!")
        except Exception as e:
            print(f"Commit falhou: {e}")
            
        # Limpar o teste
        db.rollback()
        inv.nome = old_name
        db.commit()

if __name__ == "__main__":
    test_rollback()
