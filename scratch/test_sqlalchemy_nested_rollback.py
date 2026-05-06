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
            # nested.rollback() em vez de db.rollback()
            nested.rollback()
        
        # 3. Tente fazer commit
        db.commit()
        
        # 4. Verifique se a alteração inicial foi salva
        db.refresh(inv)
        print(f"Nome do investidor pós-commit (nested.rollback): {inv.nome}")
        if inv.nome == old_name + " TEST":
            print("nested.rollback() FEZ ROLLBACK SÓ DO SAVEPOINT e a transação sobreviveu")
        else:
            print("nested.rollback() falhou em proteger a transação")
            
        # Limpar o teste
        inv.nome = old_name
        db.commit()

if __name__ == "__main__":
    test_rollback()
