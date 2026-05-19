from database import Session
from models import Projeto
with Session() as db:
    projects = db.query(Projeto).limit(5).all()
    for p in projects:
        print(f"ID: {p.pipefy_id}, Name: {p.nome}, Status: {p.status}, Moeda: {p.moeda}, Fee: {p.fee}")
