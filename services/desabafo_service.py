"""Serviço do canal Desabafo (100% anônimo).

A tabela NÃO possui qualquer campo que identifique o autor (sem e-mail,
investidor_id, IP, user-agent ou sessão). Guarda apenas o dia da publicação.
"""
from database import Session
from sqlalchemy import text

SCHEMA = "plataforma_geral"


def _serializar(row):
    return {
        "id": row["id"],
        "conteudo": row["conteudo"],
        "categoria": row["categoria"],
        "criado_dia": row["criado_dia"].isoformat() if row["criado_dia"] else None,
        "oculto": bool(row.get("oculto")),
    }


def listar(cursor=None, limite=20, incluir_ocultos=False):
    conds = ["deletado = FALSE"]
    if not incluir_ocultos:
        conds.append("oculto = FALSE")
    params = {"lim": limite}
    if cursor:
        conds.append("id < :cursor")
        params["cursor"] = int(cursor)
    sql = (
        f'SELECT id, conteudo, categoria, criado_dia, oculto FROM "{SCHEMA}".desabafo_posts '
        f"WHERE {' AND '.join(conds)} ORDER BY id DESC LIMIT :lim"
    )
    with Session() as db:
        rows = db.execute(text(sql), params).mappings().all()
    return [_serializar(r) for r in rows]


def criar(conteudo, categoria=None):
    with Session() as db:
        row = db.execute(
            text(
                f'INSERT INTO "{SCHEMA}".desabafo_posts (conteudo, categoria, criado_dia) '
                "VALUES (:c, :cat, (now() AT TIME ZONE 'America/Sao_Paulo')::date) "
                "RETURNING id, criado_dia"
            ),
            {"c": conteudo, "cat": categoria},
        ).mappings().first()
        db.commit()
    return dict(row) if row else None


def ocultar(post_id, oculto=True):
    with Session() as db:
        db.execute(
            text(f'UPDATE "{SCHEMA}".desabafo_posts SET oculto = :o WHERE id = :i'),
            {"o": bool(oculto), "i": post_id},
        )
        db.commit()


def excluir(post_id):
    with Session() as db:
        db.execute(
            text(f'DELETE FROM "{SCHEMA}".desabafo_posts WHERE id = :i'), {"i": post_id}
        )
        db.commit()