"""
Verificação e sincronização forçada para Isaac/Grunn.
Lê o snapshot atual e atualiza MetricaMensal com o valor correto.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Session
from models import MetricaMensal, InvestidorProjeto
from sqlalchemy import text
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime
import json

MES = datetime.now().month
ANO = datetime.now().year
ISAAC_EMAIL = "isaac.emanuel@v4company.com"

def sync_all_projects():
    """Sincroniza TODOS os projetos do Isaac com base no snapshot real."""
    with Session() as db:
        vinculos = db.query(InvestidorProjeto).filter_by(email_investidor=ISAAC_EMAIL).all()
        metrica = db.query(MetricaMensal).filter_by(
            email_investidor=ISAAC_EMAIL, mes=MES, ano=ANO
        ).first()
        
        if not metrica:
            print("[ERRO] MetricaMensal não encontrada!")
            return
        
        entregas_op = list(metrica.entregas_operacao or [])
        any_changed = False
        
        for v in vinculos:
            pid = v.pipefy_id_projeto
            nome = v.nome_projeto or f"Projeto {pid}"
            
            # Ler snapshot
            row = db.execute(text(
                "SELECT entregas FROM plataforma_geral.operacao "
                "WHERE id_projeto = :id AND mes = :mes AND ano = :ano LIMIT 1"
            ), {"id": str(pid), "mes": MES, "ano": ANO}).first()
            
            if not row or not row.entregas:
                continue
            
            snap = row.entregas if isinstance(row.entregas, dict) else json.loads(row.entregas)
            
            # Calcular counts
            checkins = snap.get("checkin_semanal") or []
            plano_planos = (snap.get("plano_midia") or {}).get("planos") or []
            otims = snap.get("otimizacoes") or []
            kpis_link = (snap.get("kpis") or {}).get("link") or ""
            forecasting_link = (snap.get("forecasting") or {}).get("link") or ""
            relatorio_link = (snap.get("relatorio_mensal") or {}).get("link") or ""
            relatorio_acc = (snap.get("relatorio_account") or {}).get("link") or ""
            relatorio_gt = (snap.get("relatorio_gt") or {}).get("link") or ""
            
            counts = {
                "csat_checkin": min(len(checkins), 4),
                "plano_de_midia": 1 if plano_planos else 0,
                "documento_de_otimizacao": min(len(otims), 4),
                "kpis": 1 if kpis_link else 0,
                "forecasting": 1 if forecasting_link else 0,
                "relatorio_mensal": 1 if (relatorio_link or relatorio_acc or relatorio_gt) else 0,
                "relatorio_account": 1 if (relatorio_acc or relatorio_link) else 0,
                "relatorio_gt": 1 if (relatorio_gt or relatorio_link) else 0,
                "planner_monday": 0,
            }
            
            # Achar entry na entregas_operacao
            entry = next((e for e in entregas_op if str(e.get("projeto_id")) == str(pid)), None)
            if not entry:
                continue
            
            changed = False
            for ent in entry.get("entregas", []):
                n = ent.get("nome")
                if n in counts and ent.get("entregues") != counts[n]:
                    old = ent.get("entregues")
                    ent["entregues"] = counts[n]
                    print(f"  [{nome}] {n}: {old} -> {counts[n]}")
                    changed = True
                # Corrigir meta de csat_checkin
                if n == "csat_checkin" and ent.get("meta") != 4:
                    ent["meta"] = 4
                    changed = True
            
            if changed:
                any_changed = True
        
        if any_changed:
            flag_modified(metrica, "entregas_operacao")
            db.commit()
            print("\n[OK] MetricaMensal sincronizada com sucesso!")
        else:
            print("\n[INFO] Tudo já está sincronizado")

if __name__ == "__main__":
    sync_all_projects()
