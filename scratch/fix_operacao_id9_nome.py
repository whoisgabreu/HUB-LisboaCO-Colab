"""Corrige nome da linha id=9 da tabela plataforma_geral.operacao."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

TARGET_ID = 9
EXPECTED_PIPEFY = "1295732191"

with engine.begin() as c:
    antes = c.execute(text(
        "SELECT id, id_projeto, nome FROM plataforma_geral.operacao WHERE id = :id"
    ), {"id": TARGET_ID}).fetchone()

    if not antes:
        print(f"ERRO: linha id={TARGET_ID} não existe")
        sys.exit(1)

    print(f"ANTES  -> id={antes[0]} id_projeto={antes[1]} nome={antes[2]!r}")

    if str(antes[1]) != EXPECTED_PIPEFY:
        print(f"ABORTADO: id_projeto inesperado ({antes[1]}); esperava {EXPECTED_PIPEFY}")
        sys.exit(1)

    nome_proj = c.execute(text(
        "SELECT TRIM(nome) FROM plataforma_geral.projetos_ativos "
        "WHERE pipefy_id::text = :pid LIMIT 1"
    ), {"pid": EXPECTED_PIPEFY}).scalar()

    if not nome_proj:
        print("ABORTADO: nome do projeto não encontrado em projetos_ativos")
        sys.exit(1)

    print(f"NOVO NOME -> {nome_proj!r}")

    c.execute(text(
        "UPDATE plataforma_geral.operacao SET nome = :nome "
        "WHERE id = :id AND id_projeto = :pid"
    ), {"nome": nome_proj, "id": TARGET_ID, "pid": EXPECTED_PIPEFY})

    depois = c.execute(text(
        "SELECT id, id_projeto, nome FROM plataforma_geral.operacao WHERE id = :id"
    ), {"id": TARGET_ID}).fetchone()
    print(f"DEPOIS -> id={depois[0]} id_projeto={depois[1]} nome={depois[2]!r}")
