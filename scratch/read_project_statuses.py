from database import Session
from models import Projeto
from sqlalchemy import func

def check_statuses():
    with Session() as db:
        res = db.query(Projeto.status, func.count(Projeto.status)).group_by(Projeto.status).all()
        print("Project Status Counts:")
        for status, count in res:
            print(f"Status: '{status}' -> Count: {count}")

if __name__ == "__main__":
    check_statuses()
