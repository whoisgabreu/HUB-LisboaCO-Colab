import os
import sys

# Add current workspace directory to Python path
sys.path.append(os.getcwd())

from database import Session
from models import Projeto

def test_migration():
    print("--- Simulating Refined Migration ---")
    
    with Session() as db:
        projetos = db.query(Projeto).all()
        
        counts = {'Ativos': 0, 'Onetime': 0, 'Inativos': 0, 'Unknown': 0}
        mapped_details = []
        
        for p in projetos:
            # We look at the saved fase_original if present, otherwise current fase_do_pipefy
            original_phase = (p.kanban_dados or {}).get('fase_original', p.fase_do_pipefy) or ""
            
            # Check if there is an explicit status we should trust first
            # But wait, did they have status set originally? Let's check status_original if we stored it?
            # We didn't store status_original, but we know status was set for 145 projects:
            # - Ativo (60), Inativo (75), Onetime (10)
            # Let's see: if a project's original_phase was 'Ativos', 'Inativos', or 'Onetime',
            # it means it was updated in our first run.
            
            # Let's write the classification function based on phase name:
            phase_lower = original_phase.lower()
            
            if "one time" in phase_lower or "onetime" in phase_lower:
                inferred_status = 'Onetime'
                inferred_phase = 'Onetime'
            elif any(x in phase_lower for x in ["churn", "offboarding", "perda de vendas", "debriefing"]):
                inferred_status = 'Inativo'
                inferred_phase = 'Inativos'
            elif any(x in phase_lower for x in ["ongoing", "onb", "onboarding", "ativos"]):
                inferred_status = 'Ativo'
                inferred_phase = 'Ativos'
            elif "inativo" in phase_lower:
                inferred_status = 'Inativo'
                inferred_phase = 'Inativos'
            else:
                # Fallback based on project's current status if it was set
                # or default to Ativo
                inferred_status = 'Ativo'
                inferred_phase = 'Ativos'
                
            counts[inferred_phase] += 1
            mapped_details.append((p.nome, original_phase, inferred_status, inferred_phase))
            
        print("\nSimulation Counts:")
        for phase, cnt in counts.items():
            print(f"- {phase}: {cnt}")

        print("\nSample mapping (first 20):")
        for name, orig_phase, inf_status, inf_phase in mapped_details[:20]:
            print(f"  * {name[:30]} | Phase: '{orig_phase}' -> Inferred: {inf_status} ({inf_phase})")

if __name__ == "__main__":
    test_migration()
