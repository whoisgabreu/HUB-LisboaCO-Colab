import os
import sys
from decimal import Decimal
from datetime import datetime, date

# Setup paths
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.append(root_dir)

from database import Session
from services.projeto_participacao_service import ProjektParticipacaoService # Oops, check name
from models import InvestidorProjeto, MetricaMensal

def test_sync():
    # Use ProjetoParticipacaoService (fixed name in the actual file)
    from services.projeto_participacao_service import ProjetoParticipacaoService
    
    # Run sync for March 2026
    print("Running sync for March 2026...")
    success = ProjetoParticipacaoService.sincronizar_remuneracao(3, 2026)
    print(f"Sync success: {success}")
    
    with Session() as db:
        # Find a scientist to verify
        sci = db.execute(text("SELECT email_investidor, pipefy_id_projeto FROM plataforma_geral.investidores_projetos WHERE cientista = True LIMIT 1")).fetchone()
        if sci:
            email, pid = sci
            print(f"Checking scientist: {email}, Project: {pid}")
            metrica = db.query(MetricaMensal).filter_by(email_investidor=email, mes=3, ano=2026).first()
            if metrica and metrica.historico_projetos:
                for item in metrica.historico_projetos:
                    if str(item.get("projeto_id")) == str(pid):
                        print(f"Project details: {item}")
                        if item.get("cientista") == True:
                            print("Verification SUCCESS: cientista flag found.")
                        else:
                            print("Verification FAILURE: cientista flag not found.")
        else:
            print("No scientist found in database to test.")

from sqlalchemy import text

if __name__ == "__main__":
    test_sync()
