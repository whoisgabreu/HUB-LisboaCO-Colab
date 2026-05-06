"""Verifica o que tem na tabela operacao."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

print("\n=== TABELA plataforma_geral.operacao ===\n")
with engine.connect() as c:
    rows = c.execute(text(
        "SELECT id, mes, ano, nome, id_projeto, entregas "
        "FROM plataforma_geral.operacao ORDER BY id"
    )).fetchall()

    if not rows:
        print("(tabela vazia - 0 linhas)")
    else:
        print(f"Total de linhas: {len(rows)}\n")
        for r in rows:
            print(f"id={r[0]} | mes={r[1]} | ano={r[2]} | nome={r[3]} | id_projeto={r[4]}")
            entregas = r[5] if isinstance(r[5], dict) else (json.loads(r[5]) if r[5] else {})
            for k, v in entregas.items():
                if isinstance(v, list):
                    print(f"    {k}: [{len(v)} item(s)]")
                elif isinstance(v, dict):
                    desc = ", ".join(v.keys()) if v else "vazio"
                    print(f"    {k}: {{{desc}}}")
                else:
                    print(f"    {k}: {v}")
            print()
