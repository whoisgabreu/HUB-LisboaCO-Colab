"""
Migration script: unificar a squad "Tigers" na "Phoenix" (rebrand).

Tigers foi renomeada para Phoenix. Este script consolida os vínculos nas
tabelas v1 (por nome) e v2 (por id), mantendo apenas "Phoenix".
Idempotente: pode ser reexecutado com segurança.

Run with: python scripts/merge_squad_tigers_phoenix.py
"""
import sys

sys.path.insert(0, ".")

from sqlalchemy import text

from database import engine

SCHEMA = "plataforma_geral"
DE = "Tigers"
PARA = "Phoenix"


def _table_exists(conn, table):
    return conn.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = :s AND table_name = :t)"
        ),
        {"s": SCHEMA, "t": table},
    ).scalar()


def _col_exists(conn, table, column):
    return conn.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.columns "
            "WHERE table_schema = :s AND table_name = :t AND column_name = :c)"
        ),
        {"s": SCHEMA, "t": table, "c": column},
    ).scalar()


def run():
    print(f"[Merge squad] {DE} -> {PARA}")
    with engine.begin() as conn:
        # ── v1: colunas por nome ──────────────────────────────────────────────
        if _col_exists(conn, "investidores", "squad"):
            n = conn.execute(
                text(f"UPDATE {SCHEMA}.investidores SET squad = :para WHERE squad = :de"),
                {"para": PARA, "de": DE},
            ).rowcount
            print(f"[Merge squad] investidores.squad: {n} linha(s) atualizada(s).")

        for tabela in ["projetos", "projetos_ativos", "projetos_inativos", "projetos_onetime"]:
            if _table_exists(conn, tabela) and _col_exists(conn, tabela, "squad_atribuida"):
                n = conn.execute(
                    text(f"UPDATE {SCHEMA}.{tabela} SET squad_atribuida = :para WHERE squad_atribuida = :de"),
                    {"para": PARA, "de": DE},
                ).rowcount
                print(f"[Merge squad] {tabela}.squad_atribuida: {n} linha(s) atualizada(s).")

        # ── v2: vínculos por id ───────────────────────────────────────────────
        phoenix_id = conn.execute(
            text(f"SELECT id FROM {SCHEMA}.v2_squads WHERE nome = :n"),
            {"n": PARA},
        ).scalar()
        tigers_id = conn.execute(
            text(f"SELECT id FROM {SCHEMA}.v2_squads WHERE nome = :n"),
            {"n": DE},
        ).scalar()

        if phoenix_id is None:
            print(f"[Merge squad] AVISO: squad '{PARA}' não encontrada em v2_squads.")
        if tigers_id is None:
            print(f"[Merge squad] '{DE}' não existe em v2_squads (nada a mesclar no v2).")
        else:
            # investidores
            conn.execute(
                text(
                    f"INSERT INTO {SCHEMA}.v2_investidor_squads (investidor_id, squad_id) "
                    f"SELECT investidor_id, :ph FROM {SCHEMA}.v2_investidor_squads WHERE squad_id = :tig "
                    "ON CONFLICT (investidor_id, squad_id) DO NOTHING"
                ),
                {"ph": phoenix_id, "tig": tigers_id},
            )
            del_inv = conn.execute(
                text(f"DELETE FROM {SCHEMA}.v2_investidor_squads WHERE squad_id = :tig"),
                {"tig": tigers_id},
            ).rowcount
            # projetos
            conn.execute(
                text(
                    f"INSERT INTO {SCHEMA}.v2_projeto_squads (pipefy_id, squad_id) "
                    f"SELECT pipefy_id, :ph FROM {SCHEMA}.v2_projeto_squads WHERE squad_id = :tig "
                    "ON CONFLICT (pipefy_id, squad_id) DO NOTHING"
                ),
                {"ph": phoenix_id, "tig": tigers_id},
            )
            conn.execute(
                text(f"DELETE FROM {SCHEMA}.v2_projeto_squads WHERE squad_id = :tig"),
                {"tig": tigers_id},
            )
            conn.execute(text(f"DELETE FROM {SCHEMA}.v2_squads WHERE id = :tig"), {"tig": tigers_id})
            print(f"[Merge squad] v2: links de Tigers removidos ({del_inv} vínculos de investidor) e linha excluída.")

    # ── Relatório ─────────────────────────────────────────────────────────────
    with engine.connect() as conn:
        restante_inv = conn.execute(
            text(f"SELECT COUNT(*) FROM {SCHEMA}.investidores WHERE squad = :de"),
            {"de": DE},
        ).scalar()
        restante_proj = conn.execute(
            text(f"SELECT COUNT(*) FROM {SCHEMA}.projetos WHERE squad_atribuida = :de"),
            {"de": DE},
        ).scalar()
        print(f"[Merge squad] Restante com '{DE}': investidores={restante_inv}, projetos={restante_proj}")
        print("[Merge squad] Concluído.")


if __name__ == "__main__":
    run()
