from database import Session
from models import Projeto, KanbanConfig
from services.kanban_service import KanbanService
import json

def run_tests():
    print("--- Running Kanban Status Verification ---")
    
    with Session() as db:
        service = KanbanService(db)
        
        # Test 1: Validation in update_config
        print("\nTest 1: Config Validation")
        bad_config = {
            "nome": "Fluxo Teste",
            "fases": [
                {
                    "id": "onboarding",
                    "nome": "Onboarding",
                    "ordem": 1,
                    # status_do_projeto is missing
                    "campos": []
                }
            ]
        }
        try:
            service.update_config("fluxo-projetos-teste", bad_config)
            print("❌ FAIL: Config with missing status_do_projeto was saved successfully.")
        except ValueError as e:
            print(f"✅ PASS: Config with missing status_do_projeto raised ValueError: {e}")
            
        bad_config_2 = {
            "nome": "Fluxo Teste",
            "fases": [
                {
                    "id": "onboarding",
                    "nome": "Onboarding",
                    "ordem": 1,
                    "status_do_projeto": "Invalido", # Invalid status
                    "campos": []
                }
            ]
        }
        try:
            service.update_config("fluxo-projetos-teste", bad_config_2)
            print("❌ FAIL: Config with invalid status_do_projeto was saved successfully.")
        except ValueError as e:
            print(f"✅ PASS: Config with invalid status_do_projeto raised ValueError: {e}")
            
        good_config = {
            "nome": "Fluxo Teste",
            "fases": [
                {
                    "id": "onboarding",
                    "nome": "Onboarding",
                    "ordem": 1,
                    "status_do_projeto": "Ativo",
                    "campos": []
                },
                {
                    "id": "concluido",
                    "nome": "Concluído",
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
        try:
            service.update_config("fluxo-projetos-teste", good_config)
            print("✅ PASS: Valid config was saved successfully.")
        except Exception as e:
            print(f"❌ FAIL: Valid config failed to save: {e}")

        # Test 2: Card Creation Status
        print("\nTest 2: Card Creation Status")
        try:
            # We will use the custom test board config we just created
            proj = service.create_card("fluxo-projetos-teste", "Projeto Teste Status 1", {}, "teste@admin.com")
            print(f"✅ Created project '{proj.nome}' (ID: {proj.pipefy_id}) with status '{proj.status}' (expected 'Ativo')")
            if proj.status == 'Ativo':
                print("✅ PASS: Initial status matches the first phase status_do_projeto.")
            else:
                print(f"❌ FAIL: Initial status is '{proj.status}', expected 'Ativo'.")
        except Exception as e:
            print(f"❌ FAIL: Card creation failed: {e}")
            proj = None

        # Test 3: Card Movement Status Update
        if proj:
            print("\nTest 3: Card Movement Status Update")
            try:
                # Move to completed phase (configured as Onetime)
                service.move_card(proj.pipefy_id, "concluido", {}, "teste@admin.com")
                db.refresh(proj)
                print(f"✅ Moved project to 'Concluído' phase (Onetime). Current project status: '{proj.status}' (expected 'Onetime')")
                if proj.status == 'Onetime':
                    print("✅ PASS: Project status successfully updated to 'Onetime'.")
                else:
                    print(f"❌ FAIL: Project status is '{proj.status}', expected 'Onetime'.")
                
                # Move to churn phase (configured as Inativo)
                service.move_card(proj.pipefy_id, "churn", {}, "teste@admin.com")
                db.refresh(proj)
                print(f"✅ Moved project to 'Churn' phase (Inativo). Current project status: '{proj.status}' (expected 'Inativo')")
                if proj.status == 'Inativo':
                    print("✅ PASS: Project status successfully updated to 'Inativo'.")
                else:
                    print(f"❌ FAIL: Project status is '{proj.status}', expected 'Inativo'.")
            except Exception as e:
                print(f"❌ FAIL: Card movement failed: {e}")
            
            # Clean up the test card and test board config
            print("\nTest 4: Clean up test data")
            try:
                db.delete(proj)
                cfg = db.query(KanbanConfig).filter_by(slug="fluxo-projetos-teste").first()
                if cfg:
                    db.delete(cfg)
                db.commit()
                print("✅ PASS: Test data cleaned up.")
            except Exception as e:
                print(f"❌ FAIL: Clean up failed: {e}")

if __name__ == "__main__":
    run_tests()
