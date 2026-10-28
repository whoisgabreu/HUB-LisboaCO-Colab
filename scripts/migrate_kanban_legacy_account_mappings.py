"""Migra mapeamentos legados de conta do Kanban para projetos_contas.

Converte campos cujo ``mapeamento_coluna`` é ``meta_account_id`` ou
``google_account_id`` para:
  tabela = projetos_contas
  plataforma = meta_ads | google_ads
  frente = "" (slot padrão)
  coluna = conta_id

Por padrão faz apenas dry-run. Use --apply para gravar.

Usage:
    python scripts/migrate_kanban_legacy_account_mappings.py
    python scripts/migrate_kanban_legacy_account_mappings.py --apply
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm.attributes import flag_modified

from database import Session
from models import KanbanConfig

LEGACY = {
    "meta_account_id": "meta_ads",
    "google_account_id": "google_ads",
}


def main():
    aplicar = "--apply" in sys.argv[1:]

    with Session() as db:
        configs = db.query(KanbanConfig).all()
        total = 0
        alterados = 0

        for config in configs:
            cfg = config.configuracao or {}
            mudou = False
            for fase in cfg.get("fases", []):
                for campo in fase.get("campos", []):
                    coluna = campo.get("mapeamento_coluna")
                    if coluna not in LEGACY:
                        continue
                    total += 1
                    tabela = campo.get("mapeamento_tabela") or "projetos"
                    antes = {
                        "tabela": tabela,
                        "coluna": coluna,
                        "plataforma": campo.get("mapeamento_plataforma"),
                        "frente": campo.get("mapeamento_frente"),
                    }
                    print(
                        f"[{config.slug}] fase={fase.get('nome')} campo={campo.get('label')} "
                        f"({campo.get('id')}) {antes} -> "
                        f"projetos_contas/{LEGACY[coluna]}/conta_id"
                    )
                    if not aplicar:
                        continue

                    campo["mapeamento_tabela"] = "projetos_contas"
                    campo["mapeamento_plataforma"] = LEGACY[coluna]
                    campo["mapeamento_frente"] = ""
                    campo["mapeamento_coluna"] = "conta_id"
                    if campo.get("tipo") not in ("string", "text"):
                        campo["tipo"] = "string"
                    mudou = True

            if aplicar and mudou:
                config.configuracao = cfg
                flag_modified(config, "configuracao")
                alterados += 1

        if aplicar:
            db.commit()

        print(
            f"Campos legados encontrados: {total} | configs alteradas: "
            f"{alterados if aplicar else 0} ({'APPLY' if aplicar else 'DRY-RUN'})"
        )


if __name__ == "__main__":
    main()
