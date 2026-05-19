from database import Session
from models import Investidor

def list_users():
    with Session() as db:
        users = db.query(Investidor).filter_by(ativo=True).limit(5).all()
        for u in users:
            print(f"Email: {u.email} | Pode Editar Kanban: {u.pode_editar_kanban} | Nivel Acesso: {u.nivel_acesso}")

if __name__ == "__main__":
    list_users()
