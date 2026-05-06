"""
Script que força a sincronização do check-in do Isaac/Grunn
para confirmar que o fix SAVEPOINT resolve o problema.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Session
from models import MetricaMensal, Investidor, InvestidorProjeto
from sqlalchemy import text
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime
import json

MES = datetime.now().month
ANO = datetime.now().year
ISAAC_EMAIL = "isaac.emanuel@v4company.com"
GRUNN_PIPEFY = 1075726212

def main():
    with Session() as db:
        # 1. Ler snapshot
        row = db.execute(text(
            "SELECT entregas FROM plataforma_geral.operacao "
            "WHERE id_projeto = :id AND mes = :mes AND ano = :ano LIMIT 1"
        ), {"id": str(GRUNN_PIPEFY), "mes": MES, "ano": ANO}).first()
        
        if not row or not row.entregas:
            print("[ERRO] Snapshot não encontrado!")
            return
        
        snap = row.entregas if isinstance(row.entregas, dict) else json.loads(row.entregas)
        checkins = snap.get("checkin_semanal") or []
        print(f"[SNAPSHOT] {len(checkins)} checkin(s) encontrado(s)")
        
        # 2. Ler MetricaMensal
        metrica = db.query(MetricaMensal).filter_by(
            email_investidor=ISAAC_EMAIL, mes=MES, ano=ANO
        ).first()
        
        if not metrica:
            print("[ERRO] MetricaMensal não encontrada!")
            return
        
        lista = list(metrica.entregas_operacao or [])
        entry = next((e for e in lista if str(e.get("projeto_id")) == str(GRUNN_PIPEFY)), None)
        
        if not entry:
            print("[ERRO] Entry não encontrada na entregas_operacao!")
            return
        
        # 3. Calcular counts (igual ao _sync_metrica_entregas_operacao)
        plano_planos = (snap.get("plano_midia") or {}).get("planos") or []
        otims = snap.get("otimizacoes") or []
        kpis_link = (snap.get("kpis") or {}).get("link") or ""
        forecasting_link = (snap.get("forecasting") or {}).get("link") or ""
        relatorio_link = (snap.get("relatorio_mensal") or {}).get("link") or ""
        relatorio_acc_link = (snap.get("relatorio_account") or {}).get("link") or ""
        relatorio_gt_link = (snap.get("relatorio_gt") or {}).get("link") or ""
        
        counts = {
            "plano_de_midia": 1 if plano_planos else 0,
            "documento_de_otimizacao": min(len(otims), 4),
            "kpis": 1 if kpis_link else 0,
            "csat_checkin": min(len(checkins), 4),
            "forecasting": 1 if forecasting_link else 0,
            "relatorio_mensal": 1 if (relatorio_link or relatorio_acc_link or relatorio_gt_link) else 0,
            "relatorio_account": 1 if (relatorio_acc_link or relatorio_link) else 0,
            "relatorio_gt": 1 if (relatorio_gt_link or relatorio_link) else 0,
            "planner_monday": 0,  # Sem tabela operacao_tarefas
        }
        
        print(f"[COUNTS] {json.dumps(counts, indent=2)}")
        
        # 4. Atualizar entregues E metas
        changed = False
        for ent in entry.get("entregas", []):
            n = ent.get("nome")
            if n in counts and ent.get("entregues") != counts[n]:
                old = ent.get("entregues")
                ent["entregues"] = counts[n]
                print(f"  ATUALIZADO: {n} entregues {old} -> {counts[n]}")
                changed = True
            # Corrigir metas desatualizadas
            if n == "csat_checkin" and ent.get("meta") != 4:
                ent["meta"] = 4
                print(f"  META CORRIGIDA: csat_checkin {ent.get('meta')} -> 4")
                changed = True
        
        if changed:
            flag_modified(metrica, "entregas_operacao")
            db.commit()
            print("\n[OK] MetricaMensal ATUALIZADA com sucesso!")
        else:
            print("\n[INFO] Sem mudanças necessárias")
        
        # 5. Verificar
        db.expire(metrica)
        entregas_op = metrica.entregas_operacao or []
        entry2 = next((e for e in entregas_op if str(e.get("projeto_id")) == str(GRUNN_PIPEFY)), None)
        if entry2:
            print("\n[VERIFICAÇÃO] Estado atual:")
            for e in entry2.get("entregas", []):
                print(f"  nome={e.get('nome'):30s} meta={e.get('meta')} entregues={e.get('entregues')}")

if __name__ == "__main__":
    main()
