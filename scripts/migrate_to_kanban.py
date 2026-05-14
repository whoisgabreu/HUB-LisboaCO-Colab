import os
import sys
from datetime import datetime

# Adiciona o diretório atual ao PYTHONPATH
sys.path.append(os.getcwd())

from database import Session
from models import Projeto, KanbanConfig, KanbanHistorico
from services.kanban_service import KanbanService

def migrate():
    with Session() as db:
        service = KanbanService(db)
        print("--- Iniciando Migração para Kanban Integrado ---")
        
        # 1. Garante configuração do Board
        config = service.get_board_config("fluxo-projetos")
        print(f"Configuração '{config['nome']}' garantida.")
        
        # 2. Processa projetos existentes
        projetos = db.query(Projeto).all()
        print(f"Processando {len(projetos)} projetos...")
        
        count = 0
        for p in projetos:
            # Se não tem dados de kanban, inicializa
            if not p.kanban_dados:
                p.kanban_dados = {
                    "migrado_em": datetime.now().isoformat(),
                    "fase_original": p.fase_do_pipefy
                }
            
            # Se não tem histórico, cria snapshot inicial
            has_history = db.query(KanbanHistorico).filter_by(projeto_id=p.pipefy_id).first()
            if not has_history:
                historico = KanbanHistorico(
                    projeto_id=p.pipefy_id,
                    usuario_email="sistema",
                    snapshot={
                        "evento": "migracao",
                        "fase": p.fase_do_pipefy or "Indefinida",
                        "dados": p.kanban_dados,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                db.add(historico)
                count += 1
        
        db.commit()
        print(f"Migração concluída. {count} registros de histórico criados.")

if __name__ == "__main__":
    migrate()
