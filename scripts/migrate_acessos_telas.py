"""Migration: modelo de acesso por tela (por usuario, com padroes por cargo/posicao).

Cria:
  plataforma_geral.v2_telas          (catalogo de telas)
  plataforma_geral.v2_usuario_telas  (acesso explicito do usuario)
  plataforma_geral.v2_cargo_telas    (padrao do cargo)
  plataforma_geral.v2_posicao_telas  (padrao da posicao)

Seed do catalogo + backfill dos padroes a partir das capacidades atuais
(so preenche cargos/posicoes que ainda nao tem linhas -> idempotente).

Usage:
    python scripts/migrate_acessos_telas.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine

SCHEMA = "plataforma_geral"
NIVEIS = ("nenhum", "ver", "editar")

# codigo, nome, grupo, ordem, acesso_padrao (baseline para todos)
TELAS = [
    ("feed", "Feed", "Principal", 1, "ver"),
    ("perfil", "Perfil", "Principal", 2, "ver"),
    ("minha_agenda", "Minha Agenda", "Principal", 3, "ver"),
    ("desabafo", "Desabafo", "Comunidade", 5, "ver"),
    ("metricas", "Métricas & Evolução", "Dashboard", 10, "ver"),
    ("ranking", "Painel de Ranking", "Dashboard", 11, "ver"),
    ("projetos", "Hub de Projetos", "Dashboard", 12, "ver"),
    ("kanban", "Kanban Operacional", "Dashboard", 13, "ver"),
    ("tech", "Painel TECH", "Dashboard", 14, "ver"),
    ("operacao", "Operação (Por Projeto)", "Entregas", 20, "nenhum"),
    ("criativa", "Criativa (Por Pessoa)", "Entregas", 21, "nenhum"),
    ("grupos", "Análise de Grupos", "Gestão & CS", 30, "nenhum"),
    ("cs_cx", "CS & CX", "Gestão & CS", 31, "nenhum"),
    ("nomenclaturas", "Padrão Nomenclaturas", "Ferramentas", 40, "ver"),
    ("prompts", "Prompts GT IA", "Ferramentas", 41, "ver"),
    ("usuarios", "Gerenciar Usuários", "Administração", 50, "nenhum"),
    ("squads", "Squads", "Administração", 51, "nenhum"),
    ("acessos", "Acessos & Cargos", "Administração", 52, "nenhum"),
    ("feed_config", "Configurações do Feed", "Administração", 53, "nenhum"),
    ("mrr_historico", "Histórico de MRR", "Administração", 54, "nenhum"),
    ("remuneracao", "Remuneração", "Administração", 55, "nenhum"),
    ("automacoes", "Automações", "Administração", 56, "nenhum"),
]

# Capacidade -> telas concedidas (nivel). Usado no backfill de cargos/posicoes.
CAP_TELAS = {
    "gestao_ampla": {
        "metricas": "editar", "ranking": "editar", "projetos": "editar", "kanban": "editar",
        "operacao": "editar", "criativa": "editar", "grupos": "editar", "tech": "editar", "desabafo": "editar",
        "mrr_historico": "editar", "remuneracao": "editar", "feed_config": "editar",
        "nomenclaturas": "ver", "prompts": "ver",
    },
    "gestao_squad": {
        "metricas": "editar", "ranking": "editar", "projetos": "editar", "kanban": "editar",
        "operacao": "editar", "criativa": "editar", "remuneracao": "ver",
    },
    "operacao_account": {
        "operacao": "editar", "criativa": "editar", "projetos": "ver", "kanban": "editar",
        "metricas": "ver", "ranking": "ver", "cs_cx": "ver",
    },
    "operacao_gt": {
        "operacao": "editar", "criativa": "editar", "projetos": "ver", "kanban": "editar",
        "metricas": "ver", "ranking": "ver",
    },
    "criativa": {
        "criativa": "editar", "projetos": "ver", "kanban": "ver",
    },
    "cs_cx": {
        "cs_cx": "editar", "grupos": "editar", "projetos": "ver", "metricas": "ver", "ranking": "ver",
    },
    "tech": {
        "tech": "editar", "kanban": "editar", "projetos": "ver", "metricas": "ver", "ranking": "ver",
    },
    "people": {
        "usuarios": "editar", "squads": "editar", "acessos": "ver",
    },
}

ORDEM_NIVEL = {"nenhum": 0, "ver": 1, "editar": 2}


def _criar_tabelas(conn):
    conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
    conn.execute(text(
        f'CREATE TABLE IF NOT EXISTS "{SCHEMA}".v2_telas ('
        "codigo TEXT PRIMARY KEY, nome TEXT NOT NULL, grupo TEXT, ordem INTEGER DEFAULT 0, "
        "acesso_padrao TEXT NOT NULL DEFAULT 'nenhum' "
        "CHECK (acesso_padrao IN ('nenhum','ver','editar')), ativo BOOLEAN NOT NULL DEFAULT TRUE)"
    ))
    conn.execute(text(
        f'CREATE TABLE IF NOT EXISTS "{SCHEMA}".v2_usuario_telas ('
        "investidor_id INTEGER NOT NULL REFERENCES \"%s\".investidores(id) ON DELETE CASCADE, "
        "tela TEXT NOT NULL REFERENCES \"%s\".v2_telas(codigo) ON DELETE CASCADE, "
        "nivel TEXT NOT NULL CHECK (nivel IN ('nenhum','ver','editar')), "
        "atualizado_em TIMESTAMP DEFAULT now(), PRIMARY KEY (investidor_id, tela))" % (SCHEMA, SCHEMA)
    ))
    for tabela, coluna in (("v2_cargo_telas", "cargo"), ("v2_posicao_telas", "posicao")):
        conn.execute(text(
            f'CREATE TABLE IF NOT EXISTS "{SCHEMA}".{tabela} ('
            f"{coluna} TEXT NOT NULL, tela TEXT NOT NULL REFERENCES \"{SCHEMA}\".v2_telas(codigo) ON DELETE CASCADE, "
            "nivel TEXT NOT NULL CHECK (nivel IN ('nenhum','ver','editar')), "
            f"PRIMARY KEY ({coluna}, tela))"
        ))


def _seed_telas(conn):
    for codigo, nome, grupo, ordem, padrao in TELAS:
        conn.execute(text(
            f'INSERT INTO "{SCHEMA}".v2_telas (codigo, nome, grupo, ordem, acesso_padrao, ativo) '
            "VALUES (:c, :n, :g, :o, :p, TRUE) "
            "ON CONFLICT (codigo) DO UPDATE SET nome=EXCLUDED.nome, grupo=EXCLUDED.grupo, "
            "ordem=EXCLUDED.ordem, acesso_padrao=EXCLUDED.acesso_padrao"
        ), {"c": codigo, "n": nome, "g": grupo, "o": ordem, "p": padrao})


def _nivel_max(a, b):
    return a if ORDEM_NIVEL.get(a, 0) >= ORDEM_NIVEL.get(b, 0) else b


def _mapa_por_caps(caps):
    mapa = {}
    for cap in caps:
        for tela, nivel in CAP_TELAS.get(cap, {}).items():
            mapa[tela] = _nivel_max(mapa.get(tela, "nenhum"), nivel)
    return mapa


def _backfill(conn, tabela, coluna, catalogo):
    # so preenche alvos que ainda nao tem nenhuma linha (one-time)
    alvos = [r[0] for r in conn.execute(text(f'SELECT nome FROM "{SCHEMA}"."{catalogo}" WHERE ativo = TRUE'))]
    inseridos = 0
    for alvo in alvos:
        ja = conn.execute(text(
            f'SELECT 1 FROM "{SCHEMA}"."{tabela}" WHERE "{coluna}" = :a LIMIT 1'
        ), {"a": alvo}).first()
        if ja:
            continue
        caps = [r[0] for r in conn.execute(text(
            f'SELECT capacidade FROM "{SCHEMA}"."{"v2_cargo_capacidades" if coluna == "cargo" else "v2_posicao_capacidades"}" '
            f'WHERE "{coluna}" = :a'
        ), {"a": alvo})]
        for tela, nivel in _mapa_por_caps(caps).items():
            if nivel == "nenhum":
                continue
            conn.execute(text(
                f'INSERT INTO "{SCHEMA}"."{tabela}" ("{coluna}", tela, nivel) VALUES (:a, :t, :n) '
                "ON CONFLICT DO NOTHING"
            ), {"a": alvo, "t": tela, "n": nivel})
            inseridos += 1
    return inseridos


def migrate():
    with engine.begin() as conn:
        print("Criando tabelas de acesso por tela...")
        _criar_tabelas(conn)
        print("Semeando catálogo de telas...")
        _seed_telas(conn)
        n1 = _backfill(conn, "v2_cargo_telas", "cargo", "v2_cargos")
        n2 = _backfill(conn, "v2_posicao_telas", "posicao", "v2_posicoes")
        print(f"Backfill: {n1} padrão(ões) de cargo, {n2} de posição.")

        total = conn.execute(text(f'SELECT count(*) FROM "{SCHEMA}".v2_telas')).scalar()
        print(f"Catálogo com {total} telas.")
    print("Migração concluída.")


if __name__ == "__main__":
    migrate()