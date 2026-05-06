"""Confere se o id_projeto da linha 'vazia' existe em projetos."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

with engine.connect() as c:
    print("\n=== Tabela 'projetos' / 'projetos_ativos' contém o id_projeto 1295732191? ===\n")
    for tname in ("projetos", "projetos_ativos", "projetos_inativos", "projetos_onetime"):
        try:
            r = c.execute(text(
                f"SELECT * FROM plataforma_geral.{tname} WHERE pipefy_id::text = '1295732191' LIMIT 1"
            )).fetchone()
            print(f"  {tname}: {'ENCONTRADO -> ' + str(dict(r._mapping)) if r else 'não encontrado'}")
        except Exception as e:
            print(f"  {tname}: erro -> {e}")

    print("\n=== Pesquisa por nome contendo qualquer parte (texto livre) ===\n")
    # ver se há um projeto com esse pipefy_id em qualquer schema
    r = c.execute(text(
        "SELECT table_schema, table_name FROM information_schema.columns "
        "WHERE column_name = 'pipefy_id' AND table_schema NOT IN ('pg_catalog','information_schema')"
    )).fetchall()
    for s, t in r:
        try:
            row = c.execute(text(
                f"SELECT pipefy_id, nome FROM {s}.{t} WHERE pipefy_id::text = '1295732191' LIMIT 1"
            )).fetchone()
            if row:
                print(f"  {s}.{t} -> pipefy_id={row[0]} nome={row[1]!r}")
        except Exception:
            pass
