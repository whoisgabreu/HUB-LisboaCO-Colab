"""Teste end-to-end do save na tabela operacao."""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

PROJETO_TEST = "9999999999"
MES_TEST = 99
ANO_TEST = 9999

def step(msg):
    print("\n" + "-"*70)
    print(">> " + msg)
    print("-"*70)

def cleanup():
    with engine.begin() as c:
        c.execute(text(
            "DELETE FROM plataforma_geral.operacao WHERE id_projeto = :id AND ano = :ano"
        ), {"id": PROJETO_TEST, "ano": ANO_TEST})

# 1. CONEXAO
step("1. CONEXAO COM O BANCO")
try:
    with engine.connect() as c:
        result = c.execute(text("SELECT current_database(), current_user, current_schema()")).first()
        print("  Database: " + str(result[0]))
        print("  User:     " + str(result[1]))
        print("  Schema:   " + str(result[2]))
    print("  [OK]")
except Exception as e:
    print("  [FALHOU] " + str(e))
    sys.exit(1)

# 2. VERIFICAR TABELA
step("2. VERIFICAR TABELA plataforma_geral.operacao")
try:
    with engine.connect() as c:
        cols = c.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'plataforma_geral' AND table_name = 'operacao' "
            "ORDER BY ordinal_position"
        )).fetchall()
        if not cols:
            print("  [FALHOU] TABELA NAO EXISTE!")
            sys.exit(1)
        print("  Colunas encontradas:")
        for col in cols:
            print("    - " + str(col[0]).ljust(20) + " " + str(col[1]))
    print("  [OK]")
except Exception as e:
    print("  [FALHOU] " + str(e))
    sys.exit(1)

# 3. LIMPAR
step("3. LIMPAR DADOS DE TESTE ANTERIORES")
cleanup()
print("  [OK]")

# 4. INSERT DIRETO
step("4. INSERT DIRETO via SQL puro")
try:
    test_json = {
        "plano_midia": {"budget_total": 1000, "planos": [{"canal": "TEST"}]},
        "otimizacoes": [],
        "metas": {},
    }
    with engine.begin() as c:
        c.execute(text(
            "INSERT INTO plataforma_geral.operacao (mes, ano, nome, id_projeto, entregas) "
            "VALUES (:mes, :ano, :nome, :id, CAST(:ent AS jsonb))"
        ), {
            "mes": MES_TEST, "ano": ANO_TEST, "nome": "TESTE_DIRETO",
            "id": PROJETO_TEST, "ent": json.dumps(test_json)
        })
    print("  [OK] INSERT executado")
except Exception as e:
    print("  [FALHOU] " + str(e))
    import traceback; traceback.print_exc()
    sys.exit(1)

# 5. SELECT
step("5. SELECT direto para confirmar")
try:
    with engine.connect() as c:
        row = c.execute(text(
            "SELECT id, mes, ano, nome, id_projeto, entregas FROM plataforma_geral.operacao "
            "WHERE id_projeto = :id AND ano = :ano LIMIT 1"
        ), {"id": PROJETO_TEST, "ano": ANO_TEST}).first()
        if row:
            print("  [OK] Linha encontrada:")
            print("    id         = " + str(row[0]))
            print("    mes        = " + str(row[1]))
            print("    ano        = " + str(row[2]))
            print("    nome       = " + str(row[3]))
            print("    id_projeto = " + str(row[4]))
            print("    entregas   = " + str(row[5])[:200])
        else:
            print("  [FALHOU] LINHA NAO ENCONTRADA APOS INSERT!")
            sys.exit(1)
except Exception as e:
    print("  [FALHOU] " + str(e))
    sys.exit(1)

# 6. HELPER
step("6. TESTAR _operacao_save_section (helper do app.py)")
cleanup()
try:
    from app import _operacao_save_section, _operacao_get_snapshot

    plano = {
        "budget_total": 5000,
        "planos": [
            {"canal": "Meta Ads", "nome_campanha": "Test", "%_budget": 0.5, "R$_budget": 2500, "budget_dia": 80}
        ]
    }
    print("  Chamando _operacao_save_section(" + str(PROJETO_TEST) + ", " + str(MES_TEST) + ", " + str(ANO_TEST) + ", 'plano_midia', ...)")
    result = _operacao_save_section(PROJETO_TEST, MES_TEST, ANO_TEST, "plano_midia", plano, append=False, nome="TESTE_HELPER")
    print("  Retorno: " + str(result))

    if not result:
        print("  [FALHOU] HELPER RETORNOU FALSE!")
        sys.exit(1)

    snap = _operacao_get_snapshot(PROJETO_TEST, MES_TEST, ANO_TEST)
    print("  Snapshot lido: " + json.dumps(snap, ensure_ascii=False)[:500])

    if snap and snap.get("plano_midia", {}).get("planos"):
        print("  [OK] HELPER FUNCIONA")
    else:
        print("  [FALHOU] Snapshot vazio depois do helper!")
        sys.exit(1)
except Exception as e:
    print("  [FALHOU] " + str(e))
    import traceback; traceback.print_exc()
    sys.exit(1)

# 7. LIMPEZA
step("7. LIMPEZA FINAL")
cleanup()
print("  [OK]")

print("\n" + "="*70)
print("  TODOS OS TESTES PASSARAM")
print("="*70 + "\n")
