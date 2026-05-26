from database import Session
from models import KanbanHistorico, Projeto
import json

def check():
    with Session() as db:
        print("Last 5 history entries:")
        hist = db.query(KanbanHistorico).order_by(KanbanHistorico.data_evento.desc()).limit(5).all()
        for h in hist:
            print(f"ID: {h.id} | Projeto ID: {h.projeto_id} | Data: {h.data_evento} | Usuario: {h.usuario_email}")
            print(f"Snapshot Keys: {list(h.snapshot.keys())}")
            print(f"Snapshot: {json.dumps(h.snapshot, indent=2)}")
            print("-" * 50)
            
        print("\nChecking project for last edited history's project id:")
        if hist:
            proj = db.query(Projeto).filter_by(pipefy_id=hist[0].projeto_id).first()
            if proj:
                print(f"Project Nome: {proj.nome}")
                print(f"Project kanban_dados: {json.dumps(proj.kanban_dados, indent=2)}")

if __name__ == "__main__":
    check()
