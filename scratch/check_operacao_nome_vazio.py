"""Lista linhas em plataforma_geral.operacao com nome vazio/null."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

with engine.connect() as c:
    rows = c.execute(text(
        "SELECT id, mes, ano, id_projeto, COALESCE(NULLIF(TRIM(nome), ''), '<vazio>') AS nome "
        "FROM plataforma_geral.operacao "
        "WHERE nome IS NULL OR TRIM(nome) = '' "
        "ORDER BY id"
    )).fetchall()
    if not rows:
        print("Nenhuma linha com nome vazio.")
    else:
        print(f"Linhas com nome vazio ({len(rows)}):")
        for r in rows:
            print(f"  id={r[0]} mes={r[1]} ano={r[2]} id_projeto={r[3]} nome={r[4]}")
