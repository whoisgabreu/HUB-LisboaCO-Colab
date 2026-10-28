"""Migration: contas de mídia por projeto.

Cria ``plataforma_geral.projetos_contas``, índices, trigger e a view
``vw_projetos_midia``. Idempotente.

Observações importantes do schema atual:
- ``projetos.pipefy_id`` já é PK/única.
- ``projetos_contexto.projeto_pipefy_id`` já possui FK válida para
  ``projetos(pipefy_id)`` (ON UPDATE CASCADE / ON DELETE RESTRICT).
Portanto este script NÃO recria unique/FK nessas tabelas.

Também faz o bootstrap das contas já existentes em
``projetos.meta_account_id`` e ``projetos.google_account_id``.
Nenhuma conta é marcada como principal automaticamente.

Usage:
    python scripts/migrate_projetos_contas.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

SCHEMA = "plataforma_geral"


def migrate():
    with engine.begin() as conn:
        print("Pré-checagem...")
        dup = conn.execute(text(
            f"SELECT count(*) FROM (SELECT pipefy_id FROM {SCHEMA}.projetos "
            "GROUP BY 1 HAVING count(*) > 1) x"
        )).scalar()
        orfaos = conn.execute(text(
            f"SELECT count(*) FROM {SCHEMA}.projetos_contexto c "
            f"LEFT JOIN {SCHEMA}.projetos p ON p.pipefy_id = c.projeto_pipefy_id "
            "WHERE p.pipefy_id IS NULL"
        )).scalar()
        print(f"  pipefy_id duplicados: {dup} | contextos órfãos: {orfaos}")

        print("Criando tabela projetos_contas...")
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA}.projetos_contas (
                id                SERIAL PRIMARY KEY,
                projeto_pipefy_id INTEGER      NOT NULL,
                plataforma        VARCHAR(20)  NOT NULL,
                conta_id          VARCHAR(100) NOT NULL,
                frente            VARCHAR(100) NULL,
                descricao         TEXT         NULL,
                principal         BOOLEAN      NOT NULL DEFAULT FALSE,
                ativo             BOOLEAN      NOT NULL DEFAULT TRUE,
                created_at        TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at        TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_by        VARCHAR(100) NULL,
                CONSTRAINT fk_projetos_contas_projeto
                    FOREIGN KEY (projeto_pipefy_id)
                    REFERENCES {SCHEMA}.projetos (pipefy_id)
                    ON UPDATE CASCADE ON DELETE RESTRICT,
                CONSTRAINT ck_projetos_contas_plataforma
                    CHECK (plataforma IN ('meta_ads','facebook_page','instagram','google_ads','ga4')),
                CONSTRAINT ck_projetos_contas_conta_id_digitos
                    CHECK (conta_id ~ '^[0-9]+$'),
                CONSTRAINT ck_projetos_contas_principal_ativo
                    CHECK (NOT principal OR ativo),
                CONSTRAINT uq_projetos_contas
                    UNIQUE (projeto_pipefy_id, plataforma, conta_id)
            )
        """))

        print("Criando índices...")
        conn.execute(text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS uq_projetos_contas_principal "
            f"ON {SCHEMA}.projetos_contas (projeto_pipefy_id, plataforma) WHERE principal"
        ))
        conn.execute(text(
            f"CREATE INDEX IF NOT EXISTS idx_projetos_contas_projeto "
            f"ON {SCHEMA}.projetos_contas (projeto_pipefy_id)"
        ))

        print("Criando função/trigger de updated_at...")
        conn.execute(text(f"""
            CREATE OR REPLACE FUNCTION {SCHEMA}.fn_set_updated_at()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              NEW.updated_at := CURRENT_TIMESTAMP;
              RETURN NEW;
            END;
            $$
        """))
        conn.execute(text(
            f"DROP TRIGGER IF EXISTS trg_projetos_contas_updated_at ON {SCHEMA}.projetos_contas"
        ))
        conn.execute(text(f"""
            CREATE TRIGGER trg_projetos_contas_updated_at
            BEFORE UPDATE ON {SCHEMA}.projetos_contas
            FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.fn_set_updated_at()
        """))

        print("Criando view vw_projetos_midia...")
        conn.execute(text(f"""
            CREATE OR REPLACE VIEW {SCHEMA}.vw_projetos_midia AS
            SELECT
              p.pipefy_id,
              p.nome,
              p.status,
              p.group_lid,
              p.group_name,
              COALESCE(ct.contas, '[]'::json) AS contas,
              c.id                    AS contexto_id,
              c.data_contexto,
              c.canais_midia_ativos,
              c.ids_rastreamento,
              c.must_donts_restricoes,
              c.tom_voz_posicionamento,
              c.act_meta              AS act_meta_contexto,
              c.id_google             AS id_google_contexto
            FROM {SCHEMA}.projetos p
            LEFT JOIN LATERAL (
              SELECT json_agg(json_build_object(
                       'plataforma', pc.plataforma,
                       'conta_id',   pc.conta_id,
                       'frente',     pc.frente,
                       'descricao',  pc.descricao,
                       'principal',  pc.principal)
                     ORDER BY pc.plataforma, pc.principal DESC, pc.frente, pc.id) AS contas
              FROM {SCHEMA}.projetos_contas pc
              WHERE pc.projeto_pipefy_id = p.pipefy_id
                AND pc.ativo
            ) ct ON true
            LEFT JOIN LATERAL (
              SELECT *
              FROM {SCHEMA}.projetos_contexto x
              WHERE x.projeto_pipefy_id = p.pipefy_id
              ORDER BY x.data_contexto DESC, x.id DESC
              LIMIT 1
            ) c ON true
        """))

        print("Bootstrap das contas legadas (sem principal)...")
        meta = conn.execute(text(f"""
            INSERT INTO {SCHEMA}.projetos_contas
                (projeto_pipefy_id, plataforma, conta_id, principal, ativo, updated_by)
            SELECT pipefy_id, 'meta_ads', meta_account_id, FALSE, TRUE, 'migracao'
            FROM {SCHEMA}.projetos
            WHERE meta_account_id ~ '^[0-9]+$'
            ON CONFLICT (projeto_pipefy_id, plataforma, conta_id) DO NOTHING
        """)).rowcount
        google = conn.execute(text(f"""
            INSERT INTO {SCHEMA}.projetos_contas
                (projeto_pipefy_id, plataforma, conta_id, principal, ativo, updated_by)
            SELECT pipefy_id, 'google_ads', google_account_id, FALSE, TRUE, 'migracao'
            FROM {SCHEMA}.projetos
            WHERE google_account_id ~ '^[0-9]+$'
            ON CONFLICT (projeto_pipefy_id, plataforma, conta_id) DO NOTHING
        """)).rowcount
        print(f"  inseridas: {meta} Meta | {google} Google")

        total = conn.execute(text(f"SELECT count(*) FROM {SCHEMA}.projetos_contas")).scalar()
        print(f"Total de contas na tabela: {total}")

    print("Migração de contas de mídia concluída.")


if __name__ == "__main__":
    migrate()
