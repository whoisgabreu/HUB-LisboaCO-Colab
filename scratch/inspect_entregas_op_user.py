"""Inspeciona entregas_operacao para diagnosticar mismatch de nomes."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

EMAIL = sys.argv[1] if len(sys.argv) > 1 else None

with engine.connect() as c:
    if not EMAIL:
        print("Uso: python inspect_entregas_op_user.py <email>")
        print("\nUsuários com entregas_operacao em mai/2026 (mais recentes):")
        rows = c.execute(text(
            "SELECT email_investidor, mes, ano, jsonb_array_length(entregas_operacao) AS qtd_proj "
            "FROM plataforma_geral.investidores_metricas_mensais_novo "
            "WHERE mes = 5 AND ano = 2026 AND entregas_operacao IS NOT NULL "
            "ORDER BY email_investidor LIMIT 20"
        )).fetchall()
        for r in rows:
            print(f"  {r[0]} mes={r[1]}/{r[2]} qtd_projetos={r[3]}")
        sys.exit(0)

    rec = c.execute(text(
        "SELECT entregas_operacao FROM plataforma_geral.investidores_metricas_mensais_novo "
        "WHERE email_investidor = :email AND mes = 5 AND ano = 2026"
    ), {"email": EMAIL}).fetchone()

    if not rec or not rec[0]:
        print(f"Sem entregas_operacao para {EMAIL} em 05/2026")
        sys.exit(0)

    entregas = rec[0] if isinstance(rec[0], list) else json.loads(rec[0])
    print(f"\n=== {EMAIL} | {len(entregas)} projeto(s) ===\n")
    for proj in entregas:
        print(f"--- {proj.get('cliente')} (id={proj.get('projeto_id')}) responsavel={proj.get('responsavel')} ---")
        for it in proj.get("entregas", []):
            print(f"    nome={it.get('nome')!r:<32} tipo={it.get('tipo')!r:<14} meta={it.get('meta')} entregues={it.get('entregues')}")
        print()
