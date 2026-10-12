"""Serviço isolado de histórico mensal de MRR por projeto.

Responsável por:
- capturar o snapshot do mês corrente (upsert) — job diário;
- backfill aproximado de meses passados;
- consultas agregadas para o dashboard (MRR, churn, nº de clientes, LTV).

Não altera services existentes; usa apenas a nova tabela
plataforma_geral.projeto_mrr_historico. Todas as escritas usam SQL set-based.
"""

import csv
import io
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from permissions import SCHEMA
from services.currency import CurrencyService

ANO_PLACEHOLDER = 2900

# Expressão SQL que normaliza a moeda do projeto.
_MOEDA_SQL = "COALESCE(NULLIF(upper(trim(p.moeda)), ''), 'BRL')"
# fee convertido para BRL (USD usa a cotação; demais ficam como estão).
_FEE_BRL_SQL = (
    f"CASE WHEN {_MOEDA_SQL} = 'USD' THEN p.fee * CAST(:cotacao AS numeric) ELSE p.fee END"
)
_COTACAO_SQL = (
    f"CASE WHEN {_MOEDA_SQL} = 'USD' THEN CAST(:cotacao AS numeric(10,4)) ELSE NULL END"
)
_DATA_INICIO_SQL = (
    "CASE WHEN p.data_de_inicio IS NOT NULL "
    "AND EXTRACT(YEAR FROM p.data_de_inicio) BETWEEN 1990 AND 2100 "
    "THEN p.data_de_inicio ELSE NULL END"
)
_DATA_FIM_SQL = (
    "CASE WHEN p.data_fim IS NOT NULL "
    "AND EXTRACT(YEAR FROM p.data_fim) BETWEEN 1990 AND 2100 "
    "THEN p.data_fim ELSE NULL END"
)

_COLUNAS = (
    "projeto_pipefy_id, nome_projeto, ano, mes, fee, moeda, cotacao_usd, "
    "fee_brl, status, squad_atribuida, data_inicio, data_fim"
)


class MrrHistoricoService:
    def __init__(self, db):
        self.db = db

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _cotacao(self) -> float:
        """Cotação USD→BRL apenas se houver pelo menos um projeto em USD."""
        existe_usd = self.db.execute(text(
            f"SELECT 1 FROM {SCHEMA}.projetos "
            f"WHERE upper(trim(moeda)) = 'USD' LIMIT 1"
        )).first()
        if not existe_usd:
            return 1.0
        return float(CurrencyService.get_usd_to_brl_rate())

    # ── Snapshot ───────────────────────────────────────────────────────────────

    def snapshot_mes(self, ano: int, mes: int, projeto_id: Optional[int] = None, forcar: bool = False) -> int:
        """Upsert set-based do snapshot de um mês.

        - `projeto_id`: filtra para um único projeto;
        - `forcar=True`: sobrescreve também linhas marcadas como `manual`.
        """
        cotacao = self._cotacao()
        filtro = "AND p.pipefy_id = :pid" if projeto_id is not None else ""
        guarda = "" if forcar else f"WHERE NOT {SCHEMA}.projeto_mrr_historico.manual"
        sql = f"""
            INSERT INTO {SCHEMA}.projeto_mrr_historico ({_COLUNAS})
            SELECT p.pipefy_id, p.nome, :ano, :mes,
                p.fee,
                {_MOEDA_SQL},
                {_COTACAO_SQL},
                {_FEE_BRL_SQL},
                COALESCE(p.status, 'Inativo'),
                p.squad_atribuida,
                {_DATA_INICIO_SQL},
                {_DATA_FIM_SQL}
            FROM {SCHEMA}.projetos p
            WHERE 1 = 1 {filtro}
            ON CONFLICT (projeto_pipefy_id, ano, mes) DO UPDATE SET
                nome_projeto = EXCLUDED.nome_projeto,
                fee = EXCLUDED.fee,
                moeda = EXCLUDED.moeda,
                cotacao_usd = EXCLUDED.cotacao_usd,
                fee_brl = EXCLUDED.fee_brl,
                status = EXCLUDED.status,
                squad_atribuida = EXCLUDED.squad_atribuida,
                data_inicio = EXCLUDED.data_inicio,
                data_fim = EXCLUDED.data_fim
            {guarda}
        """
        params: Dict[str, Any] = {"ano": int(ano), "mes": int(mes), "cotacao": cotacao}
        if projeto_id is not None:
            params["pid"] = int(projeto_id)
        res = self.db.execute(text(sql), params)
        self.db.commit()
        return res.rowcount

    def capturar_fee_atual(self, projeto_pipefy_id: int) -> int:
        """Captura (e força) o fee vigente do projeto no mês atual no histórico.

        Usado quando o fee muda no Hub de Projetos (fonte da verdade): o mês
        corrente passa a refletir o novo valor imediatamente, inclusive
        sobrescrevendo edição manual daquele mês.
        """
        hoje = datetime.now()
        return self.snapshot_mes(hoje.year, hoje.month, projeto_id=int(projeto_pipefy_id), forcar=True)

    def snapshot_atual(self, forcar: bool = False) -> int:
        hoje = datetime.now()
        return self.snapshot_mes(hoje.year, hoje.month)

    def _backfill_sql(self, filtro_projeto: str = "") -> str:
        """SQL do backfill conservador (set-based), opcionalmente por projeto."""
        return f"""
            WITH base AS (
                SELECT p.pipefy_id, p.nome, p.fee, p.moeda, p.status, p.squad_atribuida,
                    {_DATA_INICIO_SQL} AS inicio,
                    {_DATA_FIM_SQL} AS fim_valido
                FROM {SCHEMA}.projetos p
                WHERE p.status IN ('Ativo', 'Inativo') {filtro_projeto}
            ),
            inc AS (
                SELECT pipefy_id_projeto AS pid, MAX(inactivated_at) AS inat
                FROM {SCHEMA}.investidores_projetos
                WHERE inactivated_at IS NOT NULL
                GROUP BY pipefy_id_projeto
            ),
            calc AS (
                SELECT b.*,
                    CASE WHEN b.status = 'Inativo'
                         THEN COALESCE(b.fim_valido, i.inat)
                         ELSE NULL END AS churn
                FROM base b
                LEFT JOIN inc i ON i.pid = b.pipefy_id
            ),
            periodo AS (
                SELECT c.*,
                    date_trunc('month', GREATEST(c.inicio, make_date(:ano_inicio, 1, 1)))::date AS mes_ini,
                    date_trunc('month', COALESCE(c.churn, CURRENT_DATE))::date AS mes_fim
                FROM calc c
                WHERE c.inicio IS NOT NULL
                  AND (c.status = 'Ativo' OR c.churn IS NOT NULL)
            )
            INSERT INTO {SCHEMA}.projeto_mrr_historico ({_COLUNAS})
            SELECT p.pipefy_id, p.nome,
                EXTRACT(YEAR FROM g.m)::int,
                EXTRACT(MONTH FROM g.m)::int,
                p.fee,
                {_MOEDA_SQL},
                {_COTACAO_SQL},
                {_FEE_BRL_SQL},
                CASE WHEN p.churn IS NOT NULL
                       AND g.m = date_trunc('month', p.churn)::date
                     THEN 'Inativo' ELSE 'Ativo' END,
                p.squad_atribuida,
                p.inicio,
                p.fim_valido
            FROM periodo p
            CROSS JOIN LATERAL generate_series(p.mes_ini, p.mes_fim, interval '1 month') AS g(m)
            WHERE p.mes_ini <= p.mes_fim
            ON CONFLICT (projeto_pipefy_id, ano, mes) DO NOTHING
        """

    def _executar_backfill(self, ano_inicio: int, projeto_id: Optional[int] = None) -> int:
        cotacao = self._cotacao()
        filtro = "AND p.pipefy_id = :pid" if projeto_id is not None else ""
        params: Dict[str, Any] = {"ano_inicio": int(ano_inicio), "cotacao": cotacao}
        if projeto_id is not None:
            params["pid"] = int(projeto_id)
        antes = self.db.execute(text(f"SELECT count(*) FROM {SCHEMA}.projeto_mrr_historico")).scalar()
        self.db.execute(text(self._backfill_sql(filtro)), params)
        self.db.commit()
        depois = self.db.execute(text(f"SELECT count(*) FROM {SCHEMA}.projeto_mrr_historico")).scalar()
        return int((depois or 0) - (antes or 0))

    def backfill(self, ano_inicio: int = 2020) -> int:
        """Backfill conservador (set-based).

        - Ativos: de data_de_inicio até hoje (fee atual).
        - Inativos: apenas se houver data de encerramento (data_fim válida ou,
          na falta, o maior inactivated_at do projeto); sem data são ignorados.
        """
        return self._executar_backfill(ano_inicio)

    def backfill_projeto(self, projeto_pipefy_id: int, ano_inicio: int = 2020) -> int:
        """Backfill conservador apenas para um projeto."""
        return self._executar_backfill(ano_inicio, projeto_id=int(projeto_pipefy_id))

    # ── Consultas ──────────────────────────────────────────────────────────────

    def serie_mensal(self, ano_ini: Optional[int] = None, mes_ini: Optional[int] = None) -> List[Dict[str, Any]]:
        filtro = ""
        params: Dict[str, Any] = {}
        if ano_ini:
            filtro = "WHERE make_date(ano, mes, 1) >= make_date(:ano_ini, :mes_ini, 1)"
            params = {"ano_ini": int(ano_ini), "mes_ini": int(mes_ini or 1)}
        sql = f"""
            WITH t AS (
                SELECT projeto_pipefy_id, ano, mes, status, fee_brl,
                    LAG(status) OVER (
                        PARTITION BY projeto_pipefy_id ORDER BY ano, mes
                    ) AS prev_status
                FROM {SCHEMA}.projeto_mrr_historico
                {filtro}
            ),
            mrr AS (
                SELECT ano, mes,
                    SUM(fee_brl) FILTER (WHERE status = 'Ativo') AS mrr,
                    COUNT(*) FILTER (WHERE status = 'Ativo') AS clientes
                FROM t GROUP BY ano, mes
            ),
            churn AS (
                SELECT ano, mes,
                    SUM(fee_brl) AS churn_valor,
                    COUNT(*) AS churn_qtd
                FROM t WHERE status = 'Inativo' AND prev_status = 'Ativo'
                GROUP BY ano, mes
            )
            SELECT m.ano, m.mes, m.mrr, m.clientes,
                COALESCE(c.churn_valor, 0) AS churn,
                COALESCE(c.churn_qtd, 0) AS churn_qtd,
                LAG(m.mrr) OVER (ORDER BY m.ano, m.mes) AS mrr_anterior
            FROM mrr m LEFT JOIN churn c USING (ano, mes)
            ORDER BY m.ano, m.mes
        """
        rows = self.db.execute(text(sql), params).all()
        serie = []
        for r in rows:
            mrr = float(r.mrr or 0)
            ant = float(r.mrr_anterior) if r.mrr_anterior is not None else None
            churn = float(r.churn or 0)
            serie.append({
                "ano": r.ano,
                "mes": r.mes,
                "label": f"{int(r.mes):02d}/{r.ano}",
                "mrr": mrr,
                "clientes": int(r.clientes or 0),
                "churn": churn,
                "churn_qtd": int(r.churn_qtd or 0),
                "mrr_anterior": ant,
                "delta_mrr": (mrr - ant) if ant is not None else None,
                "churn_pct": (churn / ant) if ant else 0.0,
            })
        return serie

    def ltv_clientes(self, limite: int = 100, somente_ativos: bool = False) -> List[Dict[str, Any]]:
        filtro_status = "WHERE u.status = 'Ativo'" if somente_ativos else ""
        sql = f"""
            WITH agg AS (
                SELECT projeto_pipefy_id,
                    MAX(nome_projeto) AS nome,
                    SUM(fee_brl) FILTER (WHERE status = 'Ativo') AS ltv,
                    COUNT(*) FILTER (WHERE status = 'Ativo') AS meses_ativo,
                    MIN(make_date(ano, mes, 1)) AS primeiro_mes,
                    MAX(make_date(ano, mes, 1)) AS ultimo_mes
                FROM {SCHEMA}.projeto_mrr_historico
                GROUP BY projeto_pipefy_id
            ),
            ult AS (
                SELECT DISTINCT ON (projeto_pipefy_id)
                    projeto_pipefy_id, status, fee_brl, squad_atribuida, data_inicio, data_fim
                FROM {SCHEMA}.projeto_mrr_historico
                ORDER BY projeto_pipefy_id, ano DESC, mes DESC
            )
            SELECT a.*, u.status AS status_atual, u.fee_brl AS mrr_atual,
                u.squad_atribuida, u.data_inicio, u.data_fim
            FROM agg a JOIN ult u USING (projeto_pipefy_id)
            {filtro_status}
            ORDER BY a.ltv DESC NULLS LAST
            LIMIT :limite
        """
        rows = self.db.execute(text(sql), {"limite": int(limite)}).all()
        return [
            {
                "projeto_pipefy_id": r.projeto_pipefy_id,
                "nome": r.nome,
                "ltv": float(r.ltv or 0),
                "meses_ativo": int(r.meses_ativo or 0),
                "primeiro_mes": r.primeiro_mes.isoformat() if r.primeiro_mes else None,
                "ultimo_mes": r.ultimo_mes.isoformat() if r.ultimo_mes else None,
                "status_atual": r.status_atual,
                "mrr_atual": float(r.mrr_atual or 0),
                "squad_atribuida": r.squad_atribuida,
                "data_inicio": r.data_inicio.isoformat() if r.data_inicio else None,
                "data_fim": r.data_fim.isoformat() if r.data_fim else None,
            }
            for r in rows
        ]

    def somatorio_ltv(self, ate=None) -> Dict[int, float]:
        """{projeto_pipefy_id: LTV acumulado (Σ fee_brl de status Ativo)} até `ate` (inclusive)."""
        filtro = ""
        params: Dict[str, Any] = {}
        if ate is not None:
            filtro = "WHERE make_date(ano, mes, 1) <= :ate"
            params["ate"] = ate
        sql = f"""
            SELECT projeto_pipefy_id, SUM(fee_brl) FILTER (WHERE status = 'Ativo') AS ltv
            FROM {SCHEMA}.projeto_mrr_historico
            {filtro}
            GROUP BY projeto_pipefy_id
        """
        return {r[0]: float(r[1] or 0) for r in self.db.execute(text(sql), params).all()}

    def resumo(self) -> Dict[str, Any]:
        serie = self.serie_mensal()
        if not serie:
            return {
                "mrr_atual": 0.0, "delta_mrr": None, "clientes": 0,
                "churn_valor": 0.0, "churn_pct": 0.0, "churn_qtd": 0,
                "ltv_medio": 0.0, "numero_meses": 0, "ultimo": None,
            }
        ultimo = serie[-1]
        ltvs = [c["ltv"] for c in self.ltv_clientes(limite=1000000)]
        ltv_medio = (sum(ltvs) / len(ltvs)) if ltvs else 0.0
        return {
            "mrr_atual": ultimo["mrr"],
            "delta_mrr": ultimo["delta_mrr"],
            "clientes": ultimo["clientes"],
            "churn_valor": ultimo["churn"],
            "churn_pct": ultimo["churn_pct"],
            "churn_qtd": ultimo["churn_qtd"],
            "ltv_medio": ltv_medio,
            "numero_meses": len(serie),
            "ultimo": ultimo["label"],
        }

    # ── Edição (admin) ─────────────────────────────────────────────────────────

    @staticmethod
    def _num(v):
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().replace("R$", "").replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    @staticmethod
    def _data(v):
        if not v:
            return None
        if isinstance(v, date):
            return v
        try:
            return date.fromisoformat(str(v)[:10])
        except ValueError:
            return None

    @staticmethod
    def _txt(v):
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    def _upsert_linha(self, valores: Dict[str, Any]) -> None:
        cols = list(valores.keys())
        placeholders = ", ".join(f":{c}" for c in cols)
        updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c not in ("projeto_pipefy_id", "ano", "mes"))
        sql = f"""
            INSERT INTO {SCHEMA}.projeto_mrr_historico ({", ".join(cols)})
            VALUES ({placeholders})
            ON CONFLICT (projeto_pipefy_id, ano, mes) DO UPDATE SET {updates}
        """
        self.db.execute(text(sql), valores)

    def listar_projetos(self, busca: Optional[str] = None, limite: int = 300) -> List[Dict[str, Any]]:
        sql = f"""
            SELECT h.projeto_pipefy_id,
                MAX(h.nome_projeto) AS nome,
                COUNT(*) AS linhas,
                COUNT(*) FILTER (WHERE h.manual) AS manuais,
                MIN(make_date(h.ano, h.mes, 1)) AS inicio,
                MAX(make_date(h.ano, h.mes, 1)) AS fim
            FROM {SCHEMA}.projeto_mrr_historico h
            WHERE (:busca IS NULL OR :busca = ''
                   OR h.nome_projeto ILIKE '%' || :busca || '%'
                   OR h.projeto_pipefy_id::text LIKE '%' || :busca || '%')
            GROUP BY h.projeto_pipefy_id
            ORDER BY nome
            LIMIT :limite
        """
        rows = self.db.execute(text(sql), {"busca": busca, "limite": int(limite)}).all()
        return [{
            "projeto_pipefy_id": r.projeto_pipefy_id,
            "nome": r.nome,
            "linhas": int(r.linhas or 0),
            "manuais": int(r.manuais or 0),
            "inicio": r.inicio.isoformat() if r.inicio else None,
            "fim": r.fim.isoformat() if r.fim else None,
        } for r in rows]

    def listar_linhas(self, projeto_pipefy_id: int, ano: Optional[int] = None, mes: Optional[int] = None,
                      status: Optional[str] = None, somente_manual: bool = False) -> List[Dict[str, Any]]:
        conds = ["projeto_pipefy_id = :pid"]
        params: Dict[str, Any] = {"pid": int(projeto_pipefy_id)}
        if ano:
            conds.append("ano = :ano")
            params["ano"] = int(ano)
        if mes:
            conds.append("mes = :mes")
            params["mes"] = int(mes)
        if status:
            conds.append("status = :status")
            params["status"] = status
        if somente_manual:
            conds.append("manual = TRUE")
        sql = f"""
            SELECT ano, mes, nome_projeto, fee, moeda, cotacao_usd, fee_brl, status,
                squad_atribuida, data_inicio, data_fim, manual, editado_em, editado_por, observacao
            FROM {SCHEMA}.projeto_mrr_historico
            WHERE {" AND ".join(conds)}
            ORDER BY ano, mes
        """
        rows = self.db.execute(text(sql), params).mappings().all()
        out = []
        for r in rows:
            d = dict(r)
            d["fee"] = float(d["fee"]) if d.get("fee") is not None else None
            d["fee_brl"] = float(d["fee_brl"]) if d.get("fee_brl") is not None else None
            d["cotacao_usd"] = float(d["cotacao_usd"]) if d.get("cotacao_usd") is not None else None
            d["data_inicio"] = d["data_inicio"].isoformat() if d.get("data_inicio") else None
            d["data_fim"] = d["data_fim"].isoformat() if d.get("data_fim") else None
            d["editado_em"] = d["editado_em"].isoformat() if d.get("editado_em") else None
            out.append(d)
        return out

    def salvar_linha(self, projeto_pipefy_id, ano, mes, dados: Dict[str, Any], usuario_email=None) -> Dict[str, Any]:
        pid, ano, mes = int(projeto_pipefy_id), int(ano), int(mes)
        atual = self.db.execute(
            text(f"SELECT * FROM {SCHEMA}.projeto_mrr_historico WHERE projeto_pipefy_id=:p AND ano=:a AND mes=:m"),
            {"p": pid, "a": ano, "m": mes},
        ).mappings().first()

        if "fee" in dados:
            fee = self._num(dados.get("fee"))
        else:
            fee = float(atual["fee"]) if atual and atual["fee"] is not None else None
        moeda = (dados.get("moeda") or (atual["moeda"] if atual else None) or "BRL")
        moeda = str(moeda).strip().upper()
        if "cotacao_usd" in dados:
            cotacao = self._num(dados.get("cotacao_usd"))
        else:
            cotacao = float(atual["cotacao_usd"]) if atual and atual["cotacao_usd"] is not None else None
        if "fee_brl" in dados:
            fee_brl = self._num(dados.get("fee_brl"))
        elif fee is not None:
            if moeda == "USD":
                if cotacao is None:
                    cotacao = self._cotacao()
                fee_brl = fee * cotacao
            else:
                fee_brl = fee
        else:
            fee_brl = float(atual["fee_brl"]) if atual and atual["fee_brl"] is not None else None

        valores = {
            "projeto_pipefy_id": pid, "ano": ano, "mes": mes,
            "nome_projeto": self._txt(dados.get("nome_projeto")) if "nome_projeto" in dados else (atual["nome_projeto"] if atual else None),
            "fee": fee, "moeda": moeda, "cotacao_usd": cotacao, "fee_brl": fee_brl,
            "status": (self._txt(dados.get("status")) or "Ativo") if "status" in dados else (atual["status"] if atual else "Ativo"),
            "squad_atribuida": self._txt(dados.get("squad_atribuida")) if "squad_atribuida" in dados else (atual["squad_atribuida"] if atual else None),
            "data_inicio": self._data(dados.get("data_inicio")) if "data_inicio" in dados else (atual["data_inicio"] if atual else None),
            "data_fim": self._data(dados.get("data_fim")) if "data_fim" in dados else (atual["data_fim"] if atual else None),
            "observacao": self._txt(dados.get("observacao")) if "observacao" in dados else (atual["observacao"] if atual else None),
            "manual": True,
            "editado_em": datetime.now(),
            "editado_por": usuario_email,
        }
        self._upsert_linha(valores)
        self.db.commit()
        return {"ok": True}

    def excluir_linha(self, projeto_pipefy_id, ano, mes) -> Dict[str, Any]:
        res = self.db.execute(
            text(f"DELETE FROM {SCHEMA}.projeto_mrr_historico WHERE projeto_pipefy_id=:p AND ano=:a AND mes=:m"),
            {"p": int(projeto_pipefy_id), "a": int(ano), "m": int(mes)},
        )
        self.db.commit()
        return {"ok": True, "afetados": res.rowcount}

    def aplicar_lote(self, tipo: str, params: Dict[str, Any], usuario_email=None) -> Dict[str, Any]:
        handlers = {
            "fee": self._lote_fee, "status": self._lote_status, "churn": self._lote_churn,
            "preencher": self._lote_preencher, "excluir": self._lote_excluir,
            "reimportar": self._lote_reimportar, "resetar": self._lote_resetar,
        }
        tipo = (tipo or "").strip()
        if tipo not in handlers:
            raise ValueError("Ação inválida.")
        return handlers[tipo](params or {}, usuario_email)

    @staticmethod
    def _periodo(p: Dict[str, Any]):
        di = date(int(p["ano_ini"]), int(p["mes_ini"]), 1)
        df = date(int(p["ano_fim"]), int(p["mes_fim"]), 1)
        return di, df

    def _lote_fee(self, p: Dict[str, Any], usuario) -> Dict[str, Any]:
        pid = int(p["projeto_pipefy_id"])
        fee = self._num(p.get("fee"))
        moeda = str(p.get("moeda") or "BRL").strip().upper()
        di, df = self._periodo(p)
        cot = self._cotacao()
        res = self.db.execute(text(f"""
            UPDATE {SCHEMA}.projeto_mrr_historico SET
                fee = :fee, moeda = :moeda,
                cotacao_usd = CASE WHEN :moeda = 'USD' THEN COALESCE(cotacao_usd, :cot) ELSE NULL END,
                fee_brl = CASE WHEN :moeda = 'USD' THEN :fee * COALESCE(cotacao_usd, :cot) ELSE :fee END,
                manual = TRUE, editado_em = now(), editado_por = :user
            WHERE projeto_pipefy_id = :pid AND make_date(ano, mes, 1) BETWEEN :di AND :df
        """), {"fee": fee, "moeda": moeda, "cot": cot, "pid": pid, "di": di, "df": df, "user": usuario})
        self.db.commit()
        return {"ok": True, "afetados": res.rowcount}

    def _lote_status(self, p: Dict[str, Any], usuario) -> Dict[str, Any]:
        pid = int(p["projeto_pipefy_id"])
        status = self._txt(p.get("status")) or "Ativo"
        di, df = self._periodo(p)
        res = self.db.execute(text(f"""
            UPDATE {SCHEMA}.projeto_mrr_historico SET
                status = :status, manual = TRUE, editado_em = now(), editado_por = :user
            WHERE projeto_pipefy_id = :pid AND make_date(ano, mes, 1) BETWEEN :di AND :df
        """), {"status": status, "pid": pid, "di": di, "df": df, "user": usuario})
        self.db.commit()
        return {"ok": True, "afetados": res.rowcount}

    def _lote_churn(self, p: Dict[str, Any], usuario) -> Dict[str, Any]:
        pid = int(p["projeto_pipefy_id"])
        ano, mes = int(p["ano"]), int(p["mes"])
        churn_mes = date(ano, mes, 1)
        base = self.db.execute(text(f"""
            SELECT nome_projeto, fee, moeda, cotacao_usd, squad_atribuida, data_inicio, data_fim
            FROM {SCHEMA}.projeto_mrr_historico
            WHERE projeto_pipefy_id = :pid AND make_date(ano, mes, 1) < :churn
            ORDER BY ano DESC, mes DESC LIMIT 1
        """), {"pid": pid, "churn": churn_mes}).mappings().first()
        if not base:
            proj = self.db.execute(text(
                f"SELECT nome, fee, moeda, squad_atribuida FROM {SCHEMA}.projetos WHERE pipefy_id = :pid"
            ), {"pid": pid}).mappings().first()
            if not proj:
                raise ValueError("Projeto não encontrado.")
            base = {
                "nome_projeto": proj["nome"], "fee": proj["fee"], "moeda": proj["moeda"],
                "cotacao_usd": None, "squad_atribuida": proj["squad_atribuida"],
                "data_inicio": None, "data_fim": churn_mes,
            }
        moeda = str(base["moeda"] or "BRL").strip().upper()
        cot = float(base["cotacao_usd"]) if base["cotacao_usd"] is not None else (self._cotacao() if moeda == "USD" else None)
        fee = float(base["fee"]) if base["fee"] is not None else None
        fee_brl = (fee * cot) if (moeda == "USD" and fee is not None and cot) else fee
        self._upsert_linha({
            "projeto_pipefy_id": pid, "ano": ano, "mes": mes,
            "nome_projeto": base["nome_projeto"], "fee": fee, "moeda": moeda,
            "cotacao_usd": cot, "fee_brl": fee_brl, "status": "Inativo",
            "squad_atribuida": base["squad_atribuida"], "data_inicio": base["data_inicio"],
            "data_fim": churn_mes, "manual": True, "editado_em": datetime.now(), "editado_por": usuario,
        })
        res = self.db.execute(text(f"""
            DELETE FROM {SCHEMA}.projeto_mrr_historico
            WHERE projeto_pipefy_id = :pid AND make_date(ano, mes, 1) > :churn
        """), {"pid": pid, "churn": churn_mes})
        self.db.commit()
        return {"ok": True, "removidos": res.rowcount}

    def _lote_preencher(self, p: Dict[str, Any], usuario) -> Dict[str, Any]:
        pid = int(p["projeto_pipefy_id"])
        status = self._txt(p.get("status")) or "Ativo"
        fee = self._num(p.get("fee"))
        moeda = str(p.get("moeda") or "BRL").strip().upper()
        di, df = self._periodo(p)
        nome = self.db.execute(text(
            f"SELECT nome_projeto FROM {SCHEMA}.projeto_mrr_historico WHERE projeto_pipefy_id=:pid LIMIT 1"
        ), {"pid": pid}).scalar()
        if not nome:
            nome = self.db.execute(text(
                f"SELECT nome FROM {SCHEMA}.projetos WHERE pipefy_id=:pid"
            ), {"pid": pid}).scalar()
        cot = self._cotacao() if moeda == "USD" else None
        res = self.db.execute(text(f"""
            INSERT INTO {SCHEMA}.projeto_mrr_historico
                (projeto_pipefy_id, nome_projeto, ano, mes, fee, moeda, cotacao_usd, fee_brl,
                 status, manual, editado_em, editado_por)
            SELECT :pid, :nome, EXTRACT(YEAR FROM g.m)::int, EXTRACT(MONTH FROM g.m)::int,
                CAST(:fee AS numeric), :moeda,
                CASE WHEN :moeda = 'USD' THEN CAST(:cot AS numeric(10,4)) ELSE NULL::numeric(10,4) END,
                CASE WHEN :moeda = 'USD' THEN CAST(:fee AS numeric) * CAST(:cot AS numeric) ELSE CAST(:fee AS numeric) END,
                :status, TRUE, now(), :user
            FROM generate_series(:di, :df, interval '1 month') AS g(m)
            ON CONFLICT (projeto_pipefy_id, ano, mes) DO NOTHING
        """), {"pid": pid, "nome": nome, "fee": fee, "moeda": moeda, "cot": cot,
               "status": status, "di": di, "df": df, "user": usuario})
        self.db.commit()
        return {"ok": True, "criados": res.rowcount}

    def _lote_excluir(self, p: Dict[str, Any], usuario) -> Dict[str, Any]:
        pid = int(p["projeto_pipefy_id"])
        di, df = self._periodo(p)
        res = self.db.execute(text(f"""
            DELETE FROM {SCHEMA}.projeto_mrr_historico
            WHERE projeto_pipefy_id = :pid AND make_date(ano, mes, 1) BETWEEN :di AND :df
        """), {"pid": pid, "di": di, "df": df})
        self.db.commit()
        return {"ok": True, "afetados": res.rowcount}

    def _lote_reimportar(self, p: Dict[str, Any], usuario) -> Dict[str, Any]:
        pid = int(p["projeto_pipefy_id"])
        self.db.execute(text(
            f"DELETE FROM {SCHEMA}.projeto_mrr_historico WHERE projeto_pipefy_id = :pid"
        ), {"pid": pid})
        self.db.commit()
        criados = self.backfill_projeto(pid)
        return {"ok": True, "criados": criados}

    def _lote_resetar(self, p: Dict[str, Any], usuario) -> Dict[str, Any]:
        pid = int(p["projeto_pipefy_id"])
        conds = ["projeto_pipefy_id = :pid"]
        params: Dict[str, Any] = {"pid": pid}
        if p.get("ano_ini"):
            di, df = self._periodo(p)
            conds.append("make_date(ano, mes, 1) BETWEEN :di AND :df")
            params.update({"di": di, "df": df})
        res = self.db.execute(text(f"""
            UPDATE {SCHEMA}.projeto_mrr_historico
            SET manual = FALSE, editado_em = NULL, editado_por = NULL
            WHERE {" AND ".join(conds)}
        """), params)
        self.db.commit()
        return {"ok": True, "afetados": res.rowcount}

    def inconsistencias(self, limite: int = 500) -> List[Dict[str, Any]]:
        problemas: List[Dict[str, Any]] = []

        for r in self.db.execute(text(f"""
            WITH m AS (
                SELECT projeto_pipefy_id, ano, mes, nome_projeto,
                    make_date(ano, mes, 1) AS d,
                    LAG(make_date(ano, mes, 1)) OVER (
                        PARTITION BY projeto_pipefy_id ORDER BY ano, mes
                    ) AS prev
                FROM {SCHEMA}.projeto_mrr_historico
            )
            SELECT projeto_pipefy_id, nome_projeto AS nome, prev, d,
                ((EXTRACT(YEAR FROM d) * 12 + EXTRACT(MONTH FROM d))
                 - (EXTRACT(YEAR FROM prev) * 12 + EXTRACT(MONTH FROM prev)) - 1)::int AS faltantes
            FROM m WHERE prev IS NOT NULL AND d > prev + interval '1 month'
            ORDER BY faltantes DESC LIMIT :lim
        """), {"lim": limite}).mappings().all():
            problemas.append({
                "tipo": "lacuna", "projeto_pipefy_id": r["projeto_pipefy_id"], "nome": r["nome"],
                "ano": r["prev"].year, "mes": r["prev"].month,
                "detalhe": f"{r['faltantes']} mês(es) sem registro após {r['prev'].month:02d}/{r['prev'].year}",
                "faltantes": r["faltantes"],
            })

        for r in self.db.execute(text(f"""
            SELECT projeto_pipefy_id, nome_projeto AS nome, ano, mes
            FROM {SCHEMA}.projeto_mrr_historico
            WHERE status = 'Ativo' AND COALESCE(fee_brl, 0) = 0
            ORDER BY ano, mes LIMIT :lim
        """), {"lim": limite}).mappings().all():
            problemas.append({
                "tipo": "fee_zero", "projeto_pipefy_id": r["projeto_pipefy_id"], "nome": r["nome"],
                "ano": r["ano"], "mes": r["mes"], "detalhe": "Ativo com fee zerado",
            })

        for r in self.db.execute(text(f"""
            SELECT p.pipefy_id AS projeto_pipefy_id, p.nome, p.status
            FROM {SCHEMA}.projetos p
            LEFT JOIN {SCHEMA}.projeto_mrr_historico h ON h.projeto_pipefy_id = p.pipefy_id
            WHERE h.projeto_pipefy_id IS NULL AND p.status IN ('Ativo', 'Inativo')
            ORDER BY p.nome LIMIT :lim
        """), {"lim": limite}).mappings().all():
            problemas.append({
                "tipo": "sem_historico", "projeto_pipefy_id": r["projeto_pipefy_id"], "nome": r["nome"],
                "ano": None, "mes": None, "detalhe": f"Projeto {r['status']} sem nenhuma linha",
            })

        for r in self.db.execute(text(f"""
            WITH t AS (
                SELECT projeto_pipefy_id, nome_projeto, ano, mes, status,
                    LAG(status) OVER (PARTITION BY projeto_pipefy_id ORDER BY ano, mes) AS prev
                FROM {SCHEMA}.projeto_mrr_historico
            )
            SELECT projeto_pipefy_id, nome_projeto AS nome, ano, mes
            FROM t WHERE status = 'Inativo' AND prev IS NULL
            ORDER BY ano, mes LIMIT :lim
        """), {"lim": limite}).mappings().all():
            problemas.append({
                "tipo": "churn_orfao", "projeto_pipefy_id": r["projeto_pipefy_id"], "nome": r["nome"],
                "ano": r["ano"], "mes": r["mes"], "detalhe": "Inativo sem Ativo anterior",
            })

        return problemas

    def exportar_csv(self) -> str:
        rows = self.db.execute(text(f"""
            SELECT projeto_pipefy_id, nome_projeto, ano, mes, fee, moeda, cotacao_usd, fee_brl,
                status, data_inicio, data_fim, manual, observacao
            FROM {SCHEMA}.projeto_mrr_historico
            ORDER BY projeto_pipefy_id, ano, mes
        """)).mappings().all()
        buf = io.StringIO()
        campos = ["projeto_pipefy_id", "nome_projeto", "ano", "mes", "fee", "moeda",
                  "cotacao_usd", "fee_brl", "status", "data_inicio", "data_fim", "manual", "observacao"]
        writer = csv.DictWriter(buf, fieldnames=campos, delimiter=";")
        writer.writeheader()
        for r in rows:
            writer.writerow({c: (r[c] if r[c] is not None else "") for c in campos})
        return buf.getvalue()

    def importar_csv(self, conteudo: str, usuario_email=None) -> int:
        reader = csv.DictReader(io.StringIO(conteudo), delimiter=";")
        total = 0
        for row in reader:
            try:
                self.salvar_linha(
                    int(row["projeto_pipefy_id"]), int(row["ano"]), int(row["mes"]),
                    {
                        "nome_projeto": row.get("nome_projeto"),
                        "fee": row.get("fee"), "moeda": row.get("moeda"),
                        "fee_brl": row.get("fee_brl") or None,
                        "cotacao_usd": row.get("cotacao_usd") or None,
                        "status": row.get("status"), "observacao": row.get("observacao"),
                        "data_inicio": row.get("data_inicio") or None,
                        "data_fim": row.get("data_fim") or None,
                    },
                    usuario_email,
                )
                total += 1
            except Exception as e:
                print(f"[importar_csv] linha ignorada: {e}")
        return total
