from database import Session
from models import Projeto, KanbanConfig
from services.kanban_service import KanbanService
import json

def run_tests():
    print("--- Running Kanban Status Verification (Corrected) ---")
    
    with Session() as db:
        service = KanbanService(db)
        
        # Save original config
        orig_config_obj = db.query(KanbanConfig).filter_by(slug="fluxo-projetos").first()
        orig_config = json.loads(json.dumps(orig_config_obj.configuracao)) if orig_config_obj else None
        
        try:
            # Setup a test config on the main board slug
            test_config = {
                "nome": "Fluxo de Projetos",
                "fases": [
                    {
                        "id": "onboarding",
                        "nome": "Onboarding",
                        "ordem": 1,
                        "status_do_projeto": "Ativo",
                        "campos": []
                    },
                    {
                        "id": "execucao",
                        "nome": "Execução",
                        "ordem": 2,
                        "status_do_projeto": "Onetime",
                        "campos": []
                    },
                    {
                        "id": "churn",
                        "nome": "Churn",
                        "ordem": 3,
                        "status_do_projeto": "Inativo",
                        "campos": []
                    }
                ]
            }
            
            print("\nUpdating main board config for testing...")
            service.update_config("fluxo-projetos", test_config)
            
            # Create a card (it should use onboarding phase status, which is 'Ativo')
            print("\nTest 1: Card Creation")
            proj = service.create_card("fluxo-projetos", "Projeto Teste Status 2", {}, "teste@admin.com")
            print(f"Created project status: '{proj.status}' (expected 'Ativo')")
            assert proj.status == 'Ativo', "Initial status should be Ativo"
            
            # Move card to execution phase (Onetime)
            print("\nTest 2: Move card to Onetime phase")
            service.move_card(proj.pipefy_id, "execucao", {}, "teste@admin.com")
            db.refresh(proj)
            print(f"Project status after moving to Execução: '{proj.status}' (expected 'Onetime')")
            assert proj.status == 'Onetime', "Status should be updated to Onetime"
            
            # Move card to churn phase (Inativo)
            print("\nTest 3: Move card to Inativo phase")
            service.move_card(proj.pipefy_id, "churn", {}, "teste@admin.com")
            db.refresh(proj)
            print(f"Project status after moving to Churn: '{proj.status}' (expected 'Inativo')")
            assert proj.status == 'Inativo', "Status should be updated to Inativo"
            
            print("\n✅ ALL TESTS PASSED SUCCESSFULLY!")
            
            # Clean up project
            db.delete(proj)
            db.commit()
            
        finally:
            # Restore original config
            if orig_config:
                print("\nRestoring original config...")
                orig_config_obj = db.query(KanbanConfig).filter_by(slug="fluxo-projetos").first()
                orig_config_obj.configuracao = orig_config
                db.commit()
                print("Original config restored successfully.")

if __name__ == "__main__":
    run_tests()
