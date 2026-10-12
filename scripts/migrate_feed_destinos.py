"""
Migration script: Canais de envio do Feed (destinos).

Adiciona ``dest_todos`` e ``squads_destino`` em ``feed_posts`` e migra os posts
existentes a partir de ``visibilidade``:
  todos  -> dest_todos = TRUE
  gestao -> squads_destino = [squad "Gerência"]
  squad  -> squads_destino = squads do autor (v2_investidor_squads)

Idempotente. Run with: python scripts/migrate_feed_destinos.py
"""
import sys

sys.path.insert(0, ".")

from sqlalchemy import text

from database import engine

SCHEMA = "plataforma_geral"


def column_exists(conn, table, column):
    return conn.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.columns "
            "WHERE table_schema = :s AND table_name = :t AND column_name = :c)"
        ),
        {"s": SCHEMA, "t": table, "c": column},
    ).scalar()


def run_migration():
    print("[Migration feed destinos] Iniciando...")
    with engine.begin() as conn:
        if not column_exists(conn, "feed_posts", "dest_todos"):
            conn.execute(text(
                f"ALTER TABLE {SCHEMA}.feed_posts ADD COLUMN dest_todos BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            print("[Migration] feed_posts.dest_todos criada.")
        else:
            print("[Migration] feed_posts.dest_todos já existe.")

        if not column_exists(conn, "feed_posts", "squads_destino"):
            conn.execute(text(
                f"ALTER TABLE {SCHEMA}.feed_posts ADD COLUMN squads_destino INTEGER[] NOT NULL DEFAULT '{{}}'"
            ))
            print("[Migration] feed_posts.squads_destino criada.")
        else:
            print("[Migration] feed_posts.squads_destino já existe.")

        # Guarda: só migra posts ainda não migrados (dest_todos FALSE e squads_destino vazio)
        pendente = "dest_todos = FALSE AND COALESCE(array_length(squads_destino, 1), 0) = 0"

        n_todos = conn.execute(text(
            f"UPDATE {SCHEMA}.feed_posts SET dest_todos = TRUE WHERE visibilidade = 'todos' AND {pendente}"
        )).rowcount
        print(f"[Migration] posts 'todos' migrados: {n_todos}")

        gerencia_id = conn.execute(
            text(f"SELECT id FROM {SCHEMA}.v2_squads WHERE nome = 'Gerência'")
        ).scalar()
        n_gestao = 0
        if gerencia_id:
            n_gestao = conn.execute(
                text(f"UPDATE {SCHEMA}.feed_posts SET squads_destino = :arr WHERE visibilidade = 'gestao' AND {pendente}"),
                {"arr": [int(gerencia_id)]},
            ).rowcount
            print(f"[Migration] posts 'gestao' -> squad Gerência ({gerencia_id}): {n_gestao}")
        else:
            print("[Migration] AVISO: squad 'Gerência' não encontrada; posts 'gestao' não migrados.")

        n_squad = conn.execute(text(
            f"""
            UPDATE {SCHEMA}.feed_posts p
            SET squads_destino = sub.ids
            FROM (
                SELECT p2.id AS pid, ARRAY_AGG(DISTINCT isq.squad_id) AS ids
                FROM {SCHEMA}.feed_posts p2
                JOIN {SCHEMA}.investidores i ON i.email = p2.autor_email
                JOIN {SCHEMA}.v2_investidor_squads isq ON isq.investidor_id = i.id
                WHERE p2.visibilidade = 'squad' AND p2.dest_todos = FALSE
                      AND COALESCE(array_length(p2.squads_destino, 1), 0) = 0
                GROUP BY p2.id
            ) sub
            WHERE p.id = sub.pid
            """
        )).rowcount
        print(f"[Migration] posts 'squad' -> squads do autor: {n_squad}")

    print("[Migration feed destinos] Concluído.")


if __name__ == "__main__":
    run_migration()
