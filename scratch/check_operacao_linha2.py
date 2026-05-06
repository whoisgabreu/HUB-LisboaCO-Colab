"""Investigação somente-leitura: por que a 'linha 2' aparece vazia."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

print("\n=== 1) Todas as linhas (ORDER BY id) ===\n")
with engine.connect() as c:
    rows = c.execute(text(
        "SELECT id, mes, ano, nome, id_projeto, entregas "
        "FROM plataforma_geral.operacao ORDER BY id"
    )).fetchall()

    for idx, r in enumerate(rows, start=1):
        print(f"--- POSIÇÃO {idx} | id={r[0]} | mes={r[1]} | ano={r[2]} | nome={r[3]!r} | id_projeto={r[4]} ---")
        entregas = r[5] if isinstance(r[5], dict) else (json.loads(r[5]) if r[5] else {})
        print(json.dumps(entregas, indent=2, ensure_ascii=False)[:800])
        print()

    print("\n=== 2) Conferência de gaps de id (sequência) ===\n")
    ids = [r[0] for r in rows]
    print(f"IDs existentes: {ids}")
    print(f"IDs faltando entre 1 e {max(ids)}: {[i for i in range(1, max(ids)+1) if i not in ids]}")

    print("\n=== 3) Contagem por status de 'nome' ===\n")
    cnt = c.execute(text(
        "SELECT COUNT(*) FILTER (WHERE nome IS NULL) AS nulos, "
        "COUNT(*) FILTER (WHERE nome = '') AS vazios, "
        "COUNT(*) FILTER (WHERE nome IS NOT NULL AND nome <> '') AS preenchidos "
        "FROM plataforma_geral.operacao"
    )).fetchone()
    print(f"nome NULL: {cnt[0]} | nome '': {cnt[1]} | preenchido: {cnt[2]}")

    print("\n=== 4) Linha com id_projeto=1295732191 (a que está com nome vazio) ===\n")
    r = c.execute(text(
        "SELECT id, mes, ano, nome, id_projeto, entregas "
        "FROM plataforma_geral.operacao WHERE id_projeto = '1295732191'"
    )).fetchone()
    if r:
        print(f"id={r[0]} | nome={r[3]!r}")
        # verifica se o id_projeto existe no Pipefy/projects
        proj = c.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'plataforma_geral' AND table_name ILIKE '%projeto%'"
        )).fetchall()
        print(f"Tabelas de projeto disponíveis: {[t[0] for t in proj]}")
