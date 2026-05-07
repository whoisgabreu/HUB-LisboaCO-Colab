"""Inspeciona MF SELECT e COPETRO em abr/mai 2026 para pedro.rezende."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

EMAIL = "pedro.rezende@v4company.com"

with engine.connect() as c:
    for mes in (4, 5):
        print(f"\n========== {EMAIL} mes={mes}/2026 ==========")
        rec = c.execute(text(
            "SELECT entregas_operacao FROM plataforma_geral.investidores_metricas_mensais_novo "
            "WHERE email_investidor = :e AND mes = :m AND ano = 2026"
        ), {"e": EMAIL, "m": mes}).fetchone()
        if not rec or not rec[0]:
            print(" (sem registro)")
            continue
        entregas = rec[0] if isinstance(rec[0], list) else json.loads(rec[0])
        for proj in entregas:
            cli = (proj.get("cliente") or "").upper()
            if "COPETRO" in cli or "MF SELECT" in cli or "SELECT" in cli or "MF" == cli[:2]:
                print(f"\n--- {proj.get('cliente')} (id={proj.get('projeto_id')}) responsavel={proj.get('responsavel')} ---")
                for it in proj.get("entregas", []):
                    print(f"  nome={it.get('nome')!r:<32} tipo={it.get('tipo')!r:<14} entregues={it.get('entregues')}/{it.get('meta')}")

    print("\n========== Vínculo COPETRO/MF SELECT ==========")
    for nome in ("COPETRO", "MF SELECT"):
        rows = c.execute(text(
            "SELECT v.email_investidor, v.pipefy_id_projeto, v.cientista, v.active, p.nome "
            "FROM plataforma_geral.investidores_projetos v "
            "LEFT JOIN plataforma_geral.projetos_ativos p ON p.pipefy_id = v.pipefy_id_projeto "
            "WHERE p.nome ILIKE :n AND v.email_investidor = :e"
        ), {"n": f"%{nome}%", "e": EMAIL}).fetchall()
        for r in rows:
            print(f"  email={r[0]} pid={r[1]} cientista={r[2]} active={r[3]} nome_proj={r[4]}")
