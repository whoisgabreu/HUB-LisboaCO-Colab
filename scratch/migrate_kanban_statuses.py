from database import Session
from models import KanbanConfig
from sqlalchemy.orm.attributes import flag_modified

def migrate():
    with Session() as db:
        config = db.query(KanbanConfig).filter_by(slug="fluxo-projetos").first()
        if not config:
            print("Kanban configuration not found.")
            return
            
        print("Original configuration:")
        print(config.configuracao)
        
        fases = config.configuracao.get("fases", [])
        for fase in fases:
            phase_id = fase.get("id")
            phase_name = fase.get("nome", "").lower()
            
            if phase_id == "churn" or "churn" in phase_name or "cancelado" in phase_name or "inativo" in phase_name:
                fase["status_do_projeto"] = "Inativo"
            elif phase_id == "onetime" or "onetime" in phase_name:
                fase["status_do_projeto"] = "Onetime"
            else:
                fase["status_do_projeto"] = "Ativo"
                
            print(f"Phase: {fase.get('nome')} ({fase.get('id')}) -> status_do_projeto = '{fase['status_do_projeto']}'")
            
        flag_modified(config, "configuracao")
        db.commit()
        print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
