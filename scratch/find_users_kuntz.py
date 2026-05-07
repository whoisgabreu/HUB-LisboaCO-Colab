"""Acha quem tem KUNTZ no entregas_operacao em mai/2026."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

with engine.connect() as c:
    rows = c.execute(text(
        "SELECT email_investidor, entregas_operacao "
        "FROM plataforma_geral.investidores_metricas_mensais_novo "
        "WHERE mes = 5 AND ano = 2026 AND entregas_operacao IS NOT NULL"
    )).fetchall()

    for email, entregas_raw in rows:
        if not entregas_raw:
            continue
        entregas = entregas_raw if isinstance(entregas_raw, list) else json.loads(entregas_raw)
        for proj in entregas:
            cliente = (proj.get("cliente") or "").upper()
            pid = str(proj.get("projeto_id"))
            # KUNTZ id = 1291732048
            if pid == "1291732048" or "KUNTZ" in cliente:
                print(f"\n=== {email} | {proj.get('cliente')} | responsavel={proj.get('responsavel')} ===")
                for it in proj.get("entregas", []):
                    print(f"  nome={it.get('nome')!r:<28} tipo={it.get('tipo')!r:<12} entregues={it.get('entregues')}/{it.get('meta')}")
                # Verifica funcao do investidor
                inv = c.execute(text(
                    "SELECT funcao FROM plataforma_geral.investidores WHERE email=:e"
                ), {"e": email}).scalar()
                print(f"  -> funcao do investidor: {inv}")
                break
