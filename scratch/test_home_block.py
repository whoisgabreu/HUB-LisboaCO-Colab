import traceback
from app import app
from database import Session
from models import ProjetoAtivo, ProjetoOnetime, Investidor
from services.currency import CurrencyService

def run_test():
    with app.app_context():
        try:
            with Session() as db:
                clients_count = db.query(ProjetoAtivo).count()
                investors_count = db.query(Investidor).count()
                squads_count = db.query(ProjetoAtivo.squad_atribuida).filter(
                    ProjetoAtivo.squad_atribuida != None, 
                    ProjetoAtivo.squad_atribuida != ""
                ).distinct().count()

                from models import ProjetoOnetime
                projetos_ativos = db.query(ProjetoAtivo).all()
                projetos_onetime = db.query(ProjetoOnetime).all()
                projetos = projetos_ativos + projetos_onetime
                
                mrr_total = 0
                usd_rate = None
                for p in projetos:
                    fee = float(p.fee or 0)
                    m_code = str(p.moeda).strip().upper() if p.moeda else "BRL"
                    if m_code == 'USD':
                        if usd_rate is None:
                            usd_rate = float(CurrencyService.get_usd_to_brl_rate())
                        mrr_total += fee * usd_rate
                    else:
                        mrr_total += fee
                print(f"Success. MRR: {mrr_total}")
        except Exception as e:
            print("ERROR IN BLOCK:")
            traceback.print_exc()

if __name__ == '__main__':
    run_test()
