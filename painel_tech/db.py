import os
from contextlib import contextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from psycopg2 import pool as pg_pool
from psycopg2.extras import Json, RealDictCursor

load_dotenv()


def _fallback_db_url():
    """Reaproveita as variáveis DB_* do HUB quando DB_EXTERNAL_URL não existe."""
    from urllib.parse import quote_plus

    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    database = os.getenv("DB_DATABASE")
    user = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")
    if not all([host, port, database, user, password]):
        return None
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{database}"


DB_URL = os.getenv("DB_EXTERNAL_URL") or _fallback_db_url()
SCHEMA = os.getenv("SCHEMA", "painel_tech")
SCHEMA_SQL = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")
)
MIGRACOES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "db", "migracoes")
)

_POOL = None


def _obter_pool():
    global _POOL
    if _POOL is None:
        _POOL = pg_pool.ThreadedConnectionPool(1, 10, dsn=DB_URL)
    return _POOL

PROJETO_CAMPOS = [
    "nome",
    "descricao",
    "status",
    "responsavel_id",
    "impacto",
    "urgencia",
    "risco",
    "esforco",
    "ritmo_manual",
    "ritmo_justificativa",
    "data_inicio",
    "data_prevista_fim",
    "data_fim",
    "ordem",
]

ETAPA_CAMPOS = [
    "nome",
    "ordem",
    "responsavel_id",
    "status",
    "data_prevista",
    "data_conclusao",
    "concluida_em",
    "observacao",
    "bloqueada",
    "bloqueio_motivo",
    "bloqueio_descricao",
    "bloqueio_desde",
    "bloqueio_responsavel_id",
    "dependencia_id",
]


@contextmanager
def get_conn():
    pool = _obter_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


CAMPOS_NULOS = {
    "responsavel_id",
    "ritmo_manual",
    "ritmo_justificativa",
    "data_inicio",
    "data_prevista_fim",
    "data_fim",
    "data_prevista",
    "data_conclusao",
    "observacao",
    "bloqueio_motivo",
    "bloqueio_descricao",
    "bloqueio_desde",
    "bloqueio_responsavel_id",
}


def _limpar(coluna, valor):
    if valor == "" and coluna in CAMPOS_NULOS:
        return None
    return valor


def _fetch(sql, params=None):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return [dict(linha) for linha in cur.fetchall()]


def _fetch_one(sql, params=None):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            linha = cur.fetchone()
            return dict(linha) if linha else None


def _execute(sql, params=None):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if cur.description:
                linha = cur.fetchone()
                return dict(linha) if linha else None
            return None


def init_schema():
    with open(SCHEMA_SQL, encoding="utf-8") as arquivo:
        sql = arquivo.read()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def aplicar_migracoes():
    arquivos = (
        sorted(arquivo for arquivo in os.listdir(MIGRACOES_DIR) if arquivo.endswith(".sql"))
        if os.path.isdir(MIGRACOES_DIR)
        else []
    )
    novas = []
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')
            cur.execute(
                f'CREATE TABLE IF NOT EXISTS "{SCHEMA}".schema_migracoes ('
                "versao TEXT PRIMARY KEY, aplicada_em TIMESTAMPTZ NOT NULL DEFAULT now())"
            )
            cur.execute(f'SELECT versao FROM "{SCHEMA}".schema_migracoes')
            aplicadas = {linha[0] for linha in cur.fetchall()}
            for nome in arquivos:
                if nome in aplicadas:
                    continue
                with open(os.path.join(MIGRACOES_DIR, nome), encoding="utf-8") as arquivo:
                    cur.execute(arquivo.read())
                cur.execute(
                    f'INSERT INTO "{SCHEMA}".schema_migracoes (versao) VALUES (%s)',
                    (nome,),
                )
                novas.append(nome)
    return novas


def _montar_insert(tabela, campos, dados):
    usados = [c for c in campos if c in dados]
    colunas = ", ".join(usados)
    placeholders = ", ".join(["%s"] * len(usados))
    valores = [_limpar(c, dados[c]) for c in usados]
    sql = (
        f'INSERT INTO "{SCHEMA}"."{tabela}" ({colunas}) '
        f"VALUES ({placeholders}) RETURNING *"
    )
    return sql, valores


def _montar_update(tabela, campos, dados):
    usados = [c for c in campos if c in dados]
    sets = ", ".join(f"{c} = %s" for c in usados)
    valores = [_limpar(c, dados[c]) for c in usados]
    valores.append(dados["_id"])
    sql = f'UPDATE "{SCHEMA}"."{tabela}" SET {sets}, updated_at = now() WHERE id = %s RETURNING *'
    return sql, valores


def listar_membros():
    return _fetch(
        f'SELECT * FROM "{SCHEMA}".membros ORDER BY ativo DESC, nome'
    )


def listar_usuarios_tech():
    """Usuários do HUB com capacidade 'tech' (posição Tech ∪ cargo que concede tech)."""
    return _fetch(
        """
        SELECT DISTINCT i.id, i.nome, i.email
        FROM plataforma_geral.investidores i
        WHERE i.ativo IS TRUE AND i.id IN (
            SELECT investidor_id FROM plataforma_geral.v2_investidor_posicoes
             WHERE posicao IN (
                SELECT posicao FROM plataforma_geral.v2_posicao_capacidades WHERE capacidade = 'tech')
            UNION
            SELECT investidor_id FROM plataforma_geral.v2_investidor_cargo
             WHERE cargo IN (
                SELECT cargo FROM plataforma_geral.v2_cargo_capacidades WHERE capacidade = 'tech')
        )
        ORDER BY i.nome
        """
    )


def limpar_membros():
    _execute(f'DELETE FROM "{SCHEMA}".membros')


def criar_membro(nome, email=None, hub_user_id=None):
    return _execute(
        f'INSERT INTO "{SCHEMA}".membros (nome, email, hub_user_id) VALUES (%s, %s, %s) RETURNING *',
        (nome, email or None, hub_user_id),
    )


def excluir_membro(membro_id):
    _execute(f'DELETE FROM "{SCHEMA}".membros WHERE id = %s', (membro_id,))


def atualizar_membro_capacidade(membro_id, capacidade):
    _execute(
        f'UPDATE "{SCHEMA}".membros SET capacidade = %s WHERE id = %s',
        (capacidade, membro_id),
    )


def listar_projetos():
    return _fetch(
        f"""
        SELECT p.*, m.nome AS responsavel_nome
        FROM "{SCHEMA}".projetos p
        LEFT JOIN "{SCHEMA}".membros m ON m.id = p.responsavel_id
        ORDER BY
            CASE p.status
                WHEN 'ativo' THEN 1
                WHEN 'fila' THEN 2
                WHEN 'pausado' THEN 3
                ELSE 4
            END,
            p.ordem, p.id
        """
    )


def projetos_com_etapas():
    projetos = listar_projetos()
    mapa = etapas_por_projeto([p["id"] for p in projetos])
    return [(projeto, mapa.get(projeto["id"], [])) for projeto in projetos]


def obter_projeto(projeto_id):
    return _fetch_one(
        f"""
        SELECT p.*, m.nome AS responsavel_nome
        FROM "{SCHEMA}".projetos p
        LEFT JOIN "{SCHEMA}".membros m ON m.id = p.responsavel_id
        WHERE p.id = %s
        """,
        (projeto_id,),
    )


def criar_projeto(dados):
    dados = dict(dados)
    dados.setdefault("ordem", 0)
    sql, valores = _montar_insert("projetos", PROJETO_CAMPOS, dados)
    return _execute(sql, valores)


def atualizar_projeto(projeto_id, dados):
    dados = dict(dados)
    dados["_id"] = projeto_id
    sql, valores = _montar_update("projetos", PROJETO_CAMPOS, dados)
    return _execute(sql, valores)


def excluir_projeto(projeto_id):
    _execute(f'DELETE FROM "{SCHEMA}".projetos WHERE id = %s', (projeto_id,))


def tocar_projeto(projeto_id):
    _execute(
        f'UPDATE "{SCHEMA}".projetos SET updated_at = now() WHERE id = %s',
        (projeto_id,),
    )


def proxima_ordem_projeto():
    linha = _fetch_one(
        f'SELECT COALESCE(MAX(ordem), 0) + 1 AS prox FROM "{SCHEMA}".projetos'
    )
    return linha["prox"] if linha else 1


def atualizar_ordem_fila(ids):
    with get_conn() as conn:
        with conn.cursor() as cur:
            for posicao, projeto_id in enumerate(ids):
                cur.execute(
                    f'UPDATE "{SCHEMA}".projetos SET ordem = %s WHERE id = %s',
                    (posicao, projeto_id),
                )


def listar_etapas(projeto_id):
    return _fetch(
        f"""
        SELECT e.*, m.nome AS responsavel_nome, mb.nome AS bloqueio_responsavel_nome,
               dep.nome AS dependencia_nome
        FROM "{SCHEMA}".etapas e
        LEFT JOIN "{SCHEMA}".membros m ON m.id = e.responsavel_id
        LEFT JOIN "{SCHEMA}".membros mb ON mb.id = e.bloqueio_responsavel_id
        LEFT JOIN "{SCHEMA}".etapas dep ON dep.id = e.dependencia_id
        WHERE e.projeto_id = %s
        ORDER BY e.ordem, e.id
        """,
        (projeto_id,),
    )


def etapas_por_projeto(projeto_ids):
    if not projeto_ids:
        return {}
    linhas = _fetch(
        f"""
        SELECT e.*, m.nome AS responsavel_nome, mb.nome AS bloqueio_responsavel_nome,
               dep.nome AS dependencia_nome
        FROM "{SCHEMA}".etapas e
        LEFT JOIN "{SCHEMA}".membros m ON m.id = e.responsavel_id
        LEFT JOIN "{SCHEMA}".membros mb ON mb.id = e.bloqueio_responsavel_id
        LEFT JOIN "{SCHEMA}".etapas dep ON dep.id = e.dependencia_id
        WHERE e.projeto_id = ANY(%s)
        ORDER BY e.ordem, e.id
        """,
        (projeto_ids,),
    )
    mapa = {}
    for linha in linhas:
        mapa.setdefault(linha["projeto_id"], []).append(linha)
    return mapa


def obter_etapa(etapa_id):
    return _fetch_one(
        f'SELECT * FROM "{SCHEMA}".etapas WHERE id = %s', (etapa_id,)
    )


def criar_etapa(projeto_id, dados):
    dados = dict(dados)
    dados["projeto_id"] = projeto_id
    campos = ["projeto_id"] + ETAPA_CAMPOS
    sql, valores = _montar_insert("etapas", campos, dados)
    return _execute(sql, valores)


def atualizar_etapa(etapa_id, dados):
    dados = dict(dados)
    dados["_id"] = etapa_id
    sql, valores = _montar_update("etapas", ETAPA_CAMPOS, dados)
    return _execute(sql, valores)


def excluir_etapa(etapa_id):
    _execute(f'DELETE FROM "{SCHEMA}".etapas WHERE id = %s', (etapa_id,))


def proxima_ordem_etapa(projeto_id):
    linha = _fetch_one(
        f'SELECT COALESCE(MAX(ordem), 0) + 1 AS prox FROM "{SCHEMA}".etapas WHERE projeto_id = %s',
        (projeto_id,),
    )
    return linha["prox"] if linha else 1


def mover_etapa(etapa_id, direcao):
    etapa = obter_etapa(etapa_id)
    if not etapa:
        return
    if direcao == "cima":
        vizinha = _fetch_one(
            f"""
            SELECT * FROM "{SCHEMA}".etapas
            WHERE projeto_id = %s AND ordem < %s
            ORDER BY ordem DESC LIMIT 1
            """,
            (etapa["projeto_id"], etapa["ordem"]),
        )
    else:
        vizinha = _fetch_one(
            f"""
            SELECT * FROM "{SCHEMA}".etapas
            WHERE projeto_id = %s AND ordem > %s
            ORDER BY ordem LIMIT 1
            """,
            (etapa["projeto_id"], etapa["ordem"]),
        )
    if not vizinha:
        return
    _execute(
        f'UPDATE "{SCHEMA}".etapas SET ordem = %s WHERE id = %s',
        (vizinha["ordem"], etapa["id"]),
    )
    _execute(
        f'UPDATE "{SCHEMA}".etapas SET ordem = %s WHERE id = %s',
        (etapa["ordem"], vizinha["id"]),
    )


def registrar_evento(
    projeto_id,
    tipo,
    descricao=None,
    etapa_id=None,
    autor_id=None,
    autor_nome=None,
    payload=None,
):
    _execute(
        f'INSERT INTO "{SCHEMA}".eventos '
        "(projeto_id, etapa_id, tipo, descricao, autor_id, autor_nome, payload) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (
            projeto_id,
            etapa_id,
            tipo,
            descricao,
            autor_id,
            autor_nome,
            Json(payload) if payload is not None else None,
        ),
    )


def criar_comentario(projeto_id=None, etapa_id=None, autor_nome=None, texto=""):
    return _execute(
        f'INSERT INTO "{SCHEMA}".comentarios (projeto_id, etapa_id, autor_nome, texto) '
        "VALUES (%s, %s, %s, %s) RETURNING *",
        (projeto_id, etapa_id, autor_nome, texto),
    )


def listar_comentarios(projeto_id=None, etapa_id=None, todas=False, limite=100):
    if etapa_id is not None:
        condicao = "etapa_id = %s"
        params = (etapa_id, limite)
    elif todas:
        condicao = "projeto_id = %s"
        params = (projeto_id, limite)
    else:
        condicao = "projeto_id = %s AND etapa_id IS NULL"
        params = (projeto_id, limite)
    return _fetch(
        f'SELECT * FROM "{SCHEMA}".comentarios WHERE {condicao} '
        "ORDER BY created_at DESC LIMIT %s",
        params,
    )


def listar_eventos(projeto_id, limite=20):
    return _fetch(
        f'SELECT * FROM "{SCHEMA}".eventos WHERE projeto_id = %s '
        f"ORDER BY created_at DESC LIMIT %s",
        (projeto_id, limite),
    )


def contar_por_status():
    linhas = _fetch(
        f'SELECT status, COUNT(*) AS total FROM "{SCHEMA}".projetos GROUP BY status'
    )
    contagem = {"fila": 0, "ativo": 0, "pausado": 0, "finalizado": 0}
    for linha in linhas:
        contagem[linha["status"]] = linha["total"]
    contagem["total"] = sum(contagem.values())
    return contagem


def iniciar_sessao(projeto_id, membro_id=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f'SELECT id FROM "{SCHEMA}".tempos_sessao '
                "WHERE projeto_id = %s AND fim IS NULL",
                (projeto_id,),
            )
            if cur.fetchone():
                return False
            try:
                cur.execute(
                    f'INSERT INTO "{SCHEMA}".tempos_sessao (projeto_id, membro_id, inicio) '
                    "VALUES (%s, %s, now())",
                    (projeto_id, membro_id),
                )
            except Exception:
                return False
            return True


def pausar_sessao(projeto_id, fim=None):
    fim = fim or datetime.now(timezone.utc)
    segundos_registrados = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f'SELECT id, inicio FROM "{SCHEMA}".tempos_sessao '
                "WHERE projeto_id = %s AND fim IS NULL",
                (projeto_id,),
            )
            linhas = cur.fetchall()
            for linha in linhas:
                segundos = max(0, int((fim - linha[1]).total_seconds()))
                cur.execute(
                    f'UPDATE "{SCHEMA}".tempos_sessao SET fim = %s, segundos = %s WHERE id = %s',
                    (fim, segundos, linha[0]),
                )
                segundos_registrados += segundos
    return segundos_registrados


def tempos_resumo_por_projeto(projeto_ids):
    resumo = {projeto_id: {"total": 0, "ativas": []} for projeto_id in projeto_ids}
    if not projeto_ids:
        return resumo
    ativos = _fetch(
        f'SELECT projeto_id, inicio FROM "{SCHEMA}".tempos_sessao '
        "WHERE fim IS NULL AND projeto_id = ANY(%s) ORDER BY inicio",
        (projeto_ids,),
    )
    for linha in ativos:
        resumo[linha["projeto_id"]]["ativas"].append(linha["inicio"])
    acumulados = _fetch(
        f'SELECT projeto_id, COALESCE(SUM(segundos), 0) AS total '
        f'FROM "{SCHEMA}".tempos_sessao '
        "WHERE fim IS NOT NULL AND projeto_id = ANY(%s) GROUP BY projeto_id",
        (projeto_ids,),
    )
    for linha in acumulados:
        resumo[linha["projeto_id"]]["total"] = linha["total"]
    return resumo


def projetos_por_atividade(de, ate):
    linhas = _fetch(
        f"""
        SELECT DISTINCT projeto_id FROM (
            SELECT projeto_id FROM "{SCHEMA}".tempos_sessao
            WHERE COALESCE(fim, now()) >= %s AND inicio <= %s
            UNION
            SELECT projeto_id FROM "{SCHEMA}".eventos
            WHERE created_at >= %s AND created_at <= %s
            UNION
            SELECT projeto_id FROM "{SCHEMA}".etapas
            WHERE concluida_em >= %s AND concluida_em <= %s
        ) AS atividade
        """,
        (de, ate, de, ate, de, ate),
    )
    return [linha["projeto_id"] for linha in linhas]


def sessoes_periodo(de, ate, projeto_ids=None):
    condicao = ""
    params = [de, ate]
    if projeto_ids is not None:
        condicao = " AND projeto_id = ANY(%s)"
        params.append(list(projeto_ids))
    return _fetch(
        f"""
        SELECT s.*, p.nome AS projeto_nome, m.nome AS membro_nome
        FROM "{SCHEMA}".tempos_sessao s
        JOIN "{SCHEMA}".projetos p ON p.id = s.projeto_id
        LEFT JOIN "{SCHEMA}".membros m ON m.id = s.membro_id
        WHERE COALESCE(s.fim, now()) >= %s AND s.inicio <= %s{condicao}
        ORDER BY s.inicio
        """,
        params,
    )


def etapas_concluidas_periodo(de, ate, projeto_ids=None):
    condicao = ""
    params = [de, ate]
    if projeto_ids is not None:
        condicao = " AND e.projeto_id = ANY(%s)"
        params.append(list(projeto_ids))
    return _fetch(
        f"""
        SELECT e.*, p.nome AS projeto_nome, m.nome AS responsavel_nome
        FROM "{SCHEMA}".etapas e
        JOIN "{SCHEMA}".projetos p ON p.id = e.projeto_id
        LEFT JOIN "{SCHEMA}".membros m ON m.id = e.responsavel_id
        WHERE e.concluida_em >= %s AND e.concluida_em <= %s{condicao}
        ORDER BY e.projeto_id, e.concluida_em
        """,
        params,
    )


def eventos_periodo(de, ate, projeto_ids=None):
    condicao = ""
    params = [de, ate]
    if projeto_ids is not None:
        condicao = " AND ev.projeto_id = ANY(%s)"
        params.append(list(projeto_ids))
    return _fetch(
        f"""
        SELECT ev.*, p.nome AS projeto_nome
        FROM "{SCHEMA}".eventos ev
        JOIN "{SCHEMA}".projetos p ON p.id = ev.projeto_id
        WHERE ev.created_at >= %s AND ev.created_at <= %s{condicao}
        ORDER BY ev.created_at DESC
        """,
        params,
    )
