from database import Session
from models import KanbanHistorico, Projeto
from sqlalchemy.orm.attributes import flag_modified
import json

def test():
    with Session() as db:
        history_id = 1818 # let's test with ID 1818 or 1821
        h = db.query(KanbanHistorico).filter_by(id=history_id).first()
        if not h:
            print("History entry not found!")
            return
            
        print(f"Original snapshot: {json.dumps(h.snapshot, indent=2)}")
        
        # Simulate update
        novos_dados = {"f_1779819015302": "https://test-persisted.com"}
        snapshot = dict(h.snapshot)
        
        old_dados = snapshot.get("dados") or snapshot.get("dados_transicao") or snapshot.get("snapshot_completo") or {}
        
        snapshot_dados = snapshot.get("dados")
        if snapshot_dados is None:
            snapshot["dados"] = {}
            snapshot_dados = snapshot["dados"]
        else:
            snapshot["dados"] = dict(snapshot_dados)
            snapshot_dados = snapshot["dados"]
            
        snapshot_completo = snapshot.get("snapshot_completo")
        if snapshot_completo is not None:
            snapshot["snapshot_completo"] = dict(snapshot_completo)
            snapshot_completo = snapshot["snapshot_completo"]

        changes = {}
        for k, v in novos_dados.items():
            val_antigo = old_dados.get(k)
            if val_antigo != v:
                changes[k] = {"antes": val_antigo, "depois": v}
                snapshot_dados[k] = v
                if snapshot_completo is not None:
                    snapshot_completo[k] = v
                    
        print(f"Changes detected: {changes}")
        
        if changes:
            edicoes = snapshot.get("edicoes", [])
            edicoes.append({
                "usuario": "test@v4company.com",
                "data": "2026-05-26T15:15:00",
                "alteracoes": changes
            })
            snapshot["edicoes"] = edicoes
            h.snapshot = snapshot
            flag_modified(h, "snapshot")
            
            # Update project too
            proj = db.query(Projeto).filter_by(pipefy_id=h.projeto_id).first()
            if proj:
                proj_dados = dict(proj.kanban_dados) if proj.kanban_dados else {}
                proj_dados.update(novos_dados)
                proj.kanban_dados = proj_dados
                flag_modified(proj, "kanban_dados")
                
            db.commit()
            print("Committed successfully!")
            
    # Verify in a new session
    with Session() as db:
        h = db.query(KanbanHistorico).filter_by(id=history_id).first()
        print(f"Updated snapshot in DB: {json.dumps(h.snapshot, indent=2)}")

if __name__ == "__main__":
    test()
