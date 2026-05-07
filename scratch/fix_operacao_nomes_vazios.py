"""Preenche nome de TODAS as linhas em plataforma_geral.operacao com nome vazio,
buscando de projetos_ativos -> projetos_onetime -> projetos."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

with engine.begin() as c:
    rows = c.execute(text(
        "SELECT id, id_projeto FROM plataforma_geral.operacao "
        "WHERE nome IS NULL OR TRIM(nome) = '' ORDER BY id"
    )).fetchall()

    if not rows:
        print("Nenhuma linha vazia. Nada a corrigir.")
        sys.exit(0)

    print(f"Linhas para corrigir: {len(rows)}\n")
    for row_id, id_projeto in rows:
        nome_resolvido = None
        for tname in ("projetos_ativos", "projetos_onetime", "projetos"):
            nome_resolvido = c.execute(text(
                f"SELECT TRIM(nome) FROM plataforma_geral.{tname} "
                "WHERE pipefy_id::text = :pid LIMIT 1"
            ), {"pid": str(id_projeto)}).scalar()
            if nome_resolvido:
                origem = tname
                break

        if not nome_resolvido:
            print(f"  id={row_id} id_projeto={id_projeto} -> nome NÃO encontrado, pulando")
            continue

        c.execute(text(
            "UPDATE plataforma_geral.operacao SET nome = :nome "
            "WHERE id = :id AND id_projeto = :pid"
        ), {"nome": nome_resolvido, "id": row_id, "pid": str(id_projeto)})
        print(f"  id={row_id} id_projeto={id_projeto} -> nome='{nome_resolvido}' (de {origem})")

    print("\nConcluído.")
