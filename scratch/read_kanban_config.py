from database import Session
from models import KanbanConfig
import json

def read_config():
    with Session() as db:
        config = db.query(KanbanConfig).filter_by(slug="fluxo-projetos").first()
        if config:
            print("Kanban Config Found:")
            print(json.dumps(config.configuracao, indent=4, ensure_ascii=False))
        else:
            print("No config found for 'fluxo-projetos'.")

if __name__ == "__main__":
    read_config()
