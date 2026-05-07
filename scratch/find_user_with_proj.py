"""Acha qual usuário tem os projetos COPETRO/IRMANDADE/KUNTZ/MF SELECT/Mpa em mai/2026."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

ALVOS = ["COPETRO", "IRMANDADE", "KUNTZ", "MF SELECT", "Mpa", "MENEZELLO"]

with engine.connect() as c:
    rows = c.execute(text(
        "SELECT email_investidor, entregas_operacao "
        "FROM plataforma_geral.investidores_metricas_mensais_novo "
        "WHERE mes = 5 AND ano = 2026 AND entregas_operacao IS NOT NULL "
    )).fetchall()

    for email, entregas_raw in rows:
        if not entregas_raw:
            continue
        entregas = entregas_raw if isinstance(entregas_raw, list) else json.loads(entregas_raw)
        for proj in entregas:
            cliente = (proj.get("cliente") or "").upper()
            if any(a.upper() in cliente for a in ALVOS):
                print(f"\n>>> {email} | projeto={proj.get('cliente')} (id={proj.get('projeto_id')}) responsavel={proj.get('responsavel')}")
                for it in proj.get("entregas", []):
                    print(f"    nome={it.get('nome')!r:<32} tipo={it.get('tipo')!r:<14} meta={it.get('meta')} entregues={it.get('entregues')}")
                break
