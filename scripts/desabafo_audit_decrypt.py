"""Descriptografa uma auditoria do Desabafo usando a chave PGP privada local.

Uso:
    python scripts/desabafo_audit_decrypt.py --ref <audit_ref>

A chave privada deve estar no chaveiro GPG do desenvolvedor, protegida por
passphrase. O script não contém nem armazena a chave privada.
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from sqlalchemy import text
from database import engine

SCHEMA = "plataforma_geral"


def main():
    parser = argparse.ArgumentParser(description="Descriptografa uma auditoria do Desabafo.")
    parser.add_argument("--ref", required=True, help="audit_ref exibido no Hub")
    parser.add_argument("--gpg-homedir", default=None, help="GNUPGHOME alternativo")
    args = parser.parse_args()

    with engine.connect() as conn:
        row = conn.execute(
            text(
                f'SELECT post_id, audit_ref, ciphertext, key_id, created_at '
                f'FROM "{SCHEMA}".desabafo_audit WHERE audit_ref = :ref'
            ),
            {"ref": args.ref},
        ).mappings().first()

    if not row:
        raise SystemExit("Auditoria não encontrada para esse audit_ref.")

    cmd = ["gpg", "--decrypt"]
    env = os.environ.copy()
    if args.gpg_homedir:
        env["GNUPGHOME"] = args.gpg_homedir

    proc = subprocess.run(
        cmd,
        input=bytes(row["ciphertext"]),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    if proc.returncode != 0:
        sys.stderr.buffer.write(proc.stderr)
        raise SystemExit("Falha ao descriptografar com a chave privada local.")

    texto = proc.stdout.decode("utf-8", errors="replace")
    try:
        dados = json.loads(texto)
        print(json.dumps(dados, ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(texto)


if __name__ == "__main__":
    main()
