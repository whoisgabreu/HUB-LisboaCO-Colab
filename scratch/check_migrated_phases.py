import sys
import os
sys.path.append(os.getcwd())
from database import Session
from models import Projeto
from sqlalchemy import func

def check_history():
    with Session() as db:
        # Check projects that originally had no status
        # Since we ran our script, these are projects that now have status = 'Ativo' (since we set it to 'Ativo' when status was NULL)
        # Let's see what their fase_original was.
        projects = db.query(Projeto).all()
        
        legacy_phases = {}
        for p in projects:
            original_phase = (p.kanban_dados or {}).get('fase_original')
            if original_phase:
                legacy_phases[original_phase] = legacy_phases.get(original_phase, 0) + 1
                
        print("Legacy Phase Counts for Migrated Projects:")
        for phase, count in sorted(legacy_phases.items(), key=lambda x: x[1], reverse=True):
            print(f"- {phase}: {count}")

if __name__ == "__main__":
    check_history();
