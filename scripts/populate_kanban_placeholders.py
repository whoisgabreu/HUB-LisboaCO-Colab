import os
import sys
from datetime import datetime

# Add current workspace directory to Python path
sys.path.append(os.getcwd())

from database import Session
from models import Projeto, KanbanHistorico
from sqlalchemy.orm.attributes import flag_modified

def migrate():
    print("--- Starting Refined Kanban Phase Population Script ---")
    
    with Session() as db:
        projetos = db.query(Projeto).all()
        print(f"Total projects found: {len(projetos)}")
        
        updated_count = 0
        skipped_count = 0
        counts_by_phase = {'Ativos': 0, 'Onetime': 0, 'Inativos': 0}
        
        for p in projetos:
            # We look at the saved fase_original if present, otherwise current fase_do_pipefy
            original_phase = (p.kanban_dados or {}).get('fase_original', p.fase_do_pipefy) or ""
            
            # Classification logic based on the original phase string
            phase_lower = original_phase.lower()
            
            if "one time" in phase_lower or "onetime" in phase_lower:
                target_status = 'Onetime'
                target_phase = 'Onetime'
            elif any(x in phase_lower for x in ["churn", "offboarding", "perda de vendas", "debriefing"]):
                target_status = 'Inativo'
                target_phase = 'Inativos'
            elif any(x in phase_lower for x in ["ongoing", "onb", "onboarding", "ativos"]):
                target_status = 'Ativo'
                target_phase = 'Ativos'
            elif "inativo" in phase_lower:
                target_status = 'Inativo'
                target_phase = 'Inativos'
            else:
                # Fallback based on current status if it was set
                if p.status in ['Ativo', 'Onetime', 'Inativo']:
                    target_status = p.status
                    target_phase = 'Ativos' if p.status == 'Ativo' else ('Inativos' if p.status == 'Inativo' else 'Onetime')
                else:
                    target_status = 'Ativo'
                    target_phase = 'Ativos'
            
            # Initialize kanban_dados if null
            if p.kanban_dados is None:
                p.kanban_dados = {}
                
            # Check if any fields actually need updates
            needs_update = (p.fase_do_pipefy != target_phase) or (p.status != target_status)
            
            if not needs_update:
                skipped_count += 1
                counts_by_phase[target_phase] += 1
                continue
                
            # Keep track of original legacy phase in kanban_dados if not already set
            if 'fase_original' not in p.kanban_dados and original_phase and original_phase not in ['Ativos', 'Onetime', 'Inativos']:
                p.kanban_dados['fase_original'] = original_phase
                
            p.fase_do_pipefy = target_phase
            p.status = target_status
            flag_modified(p, 'kanban_dados')
            
            # Create a transition audit history entry
            now = datetime.now()
            historico = KanbanHistorico(
                projeto_id=p.pipefy_id,
                usuario_email="sistema",
                data_evento=now,
                snapshot={
                    "evento": "migracao_placeholder",
                    "fase_anterior": original_phase or "Nenhuma",
                    "fase_nova": target_phase,
                    "status_novo": target_status,
                    "dados": p.kanban_dados,
                    "timestamp": now.isoformat()
                }
            )
            db.add(historico)
            
            updated_count += 1
            counts_by_phase[target_phase] += 1
            
        print("\nCommitting changes...")
        db.commit()
        print("Commit completed successfully.")
        
        print("\nSummary of execution:")
        print(f"- Total Projects Updated: {updated_count}")
        print(f"- Total Projects Skipped (already correct): {skipped_count}")
        print(f"- Final projects per phase:")
        for phase, cnt in counts_by_phase.items():
            print(f"  * {phase}: {cnt}")
            
if __name__ == "__main__":
    migrate()
