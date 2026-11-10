"""Serviço do canal Desabafo.

Os posts públicos continuam sem autor. Em paralelo, uma tabela separada guarda
um ciphertext PGP com mensagem, nome e e-mail para auditoria restrita. O
ciphertext não é retornado pela API.
"""
import json
import os
import secrets
from datetime import datetime, timezone

from database import Session
from sqlalchemy import text

SCHEMA = "plataforma_geral"


class DesabafoAuditConfigError(RuntimeError):
    pass


def _audit_public_key() -> str:
    chave = (os.getenv("DESABAFO_AUDIT_PUBLIC_KEY") or "").strip()
    if not chave:
        caminho = (os.getenv("DESABAFO_AUDIT_PUBLIC_KEY_FILE") or "").strip()
        if caminho:
            with open(caminho, "r", encoding="utf-8") as fh:
                chave = fh.read().strip()
    if not chave:
        raise DesabafoAuditConfigError(
            "Configure DESABAFO_AUDIT_PUBLIC_KEY ou DESABAFO_AUDIT_PUBLIC_KEY_FILE."
        )
    return chave


def _audit_key_id() -> str:
    return (os.getenv("DESABAFO_AUDIT_KEY_ID") or "default").strip()


def _serializar(row, incluir_audit_ref=False):
    out = {
        "id": row["id"],
        "conteudo": row["conteudo"],
        "categoria": row["categoria"],
        "criado_dia": row["criado_dia"].isoformat() if row["criado_dia"] else None,
        "oculto": bool(row.get("oculto")),
    }
    if incluir_audit_ref:
        out["audit_ref"] = row.get("audit_ref")
    return out


def listar(cursor=None, limite=20, incluir_ocultos=False, incluir_audit_ref=False):
    conds = ["deletado = FALSE"]
    if not incluir_ocultos:
        conds.append("oculto = FALSE")
    params = {"lim": limite}
    if cursor:
        conds.append("id < :cursor")
        params["cursor"] = int(cursor)
    sql = (
        f'SELECT id, conteudo, categoria, criado_dia, oculto, audit_ref '
        f'FROM "{SCHEMA}".desabafo_posts '
        f"WHERE {' AND '.join(conds)} ORDER BY id DESC LIMIT :lim"
    )
    with Session() as db:
        rows = db.execute(text(sql), params).mappings().all()
    return [_serializar(r, incluir_audit_ref) for r in rows]


def criar(conteudo, categoria=None, autor_nome=None, autor_email=None):
    """Cria o post e o registro cifrado de auditoria na mesma transação."""
    public_key = _audit_public_key()
    key_id = _audit_key_id()
    audit_ref = secrets.token_hex(16)

    with Session() as db:
        try:
            row = db.execute(
                text(
                    f'INSERT INTO "{SCHEMA}".desabafo_posts '
                    "(conteudo, categoria, criado_dia) "
                    "VALUES (:c, :cat, (now() AT TIME ZONE 'America/Sao_Paulo')::date) "
                    "RETURNING id, criado_dia"
                ),
                {"c": conteudo, "cat": categoria},
            ).mappings().first()
            if not row:
                raise RuntimeError("Não foi possível criar o post.")

            payload = json.dumps(
                {
                    "v": 1,
                    "post_id": row["id"],
                    "conteudo": conteudo,
                    "categoria": categoria,
                    "criado_dia": row["criado_dia"].isoformat() if row["criado_dia"] else None,
                    "criado_em": datetime.now(timezone.utc).isoformat(),
                    "autor_nome": (autor_nome or "").strip(),
                    "autor_email": (autor_email or "").strip(),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )

            ciphertext = db.execute(
                text(
                    "SELECT pgp_pub_encrypt(:payload, dearmor(:pubkey), "
                    "'cipher-algo=aes256') AS ciphertext"
                ),
                {"payload": payload, "pubkey": public_key},
            ).scalar()
            if ciphertext is None:
                raise RuntimeError("Falha ao criptografar a auditoria.")

            db.execute(
                text(
                    f'INSERT INTO "{SCHEMA}".desabafo_audit '
                    "(post_id, audit_ref, ciphertext, key_id) "
                    "VALUES (:pid, :ref, :cipher, :key)"
                ),
                {
                    "pid": row["id"],
                    "ref": audit_ref,
                    "cipher": ciphertext,
                    "key": key_id,
                },
            )
            db.execute(
                text(
                    f'UPDATE "{SCHEMA}".desabafo_posts '
                    "SET audit_ref = :ref WHERE id = :pid"
                ),
                {"ref": audit_ref, "pid": row["id"]},
            )
            db.commit()
            return {
                "id": row["id"],
                "criado_dia": row["criado_dia"].isoformat() if row["criado_dia"] else None,
                "audit_ref": audit_ref,
            }
        except Exception:
            db.rollback()
            raise


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
