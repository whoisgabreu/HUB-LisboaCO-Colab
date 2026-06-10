from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from flask_apscheduler import APScheduler
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from collections import defaultdict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime as dt, timedelta
from requests_oauthlib import OAuth2Session
from dotenv import load_dotenv
import os
import json
import uuid

load_dotenv()

from database import Session, engine, Base
from models import (
    Investidor, Auth, Projeto,
    InvestidorProjeto, MetricaMensal, RemuneracaoCargo,

    OperacaoTarefa, OperacaoEntregaMensal, OperacaoPlanoMidia,
    OperacaoOtimizacao, OperacaoCheckin,
    MonthlyDelivery, OperacaoLinkUtil, EntregaCriativa,
    KanbanConfig, KanbanHistorico, Automacao, AutomacaoLog,
    UserFace, FaceAuthLog
)

from services.remuneracao import calcular_metricas_mensais
from services.operacao_service import OperacaoService, OperacaoSnapshotService
from services.projeto_participacao_service import ProjetoParticipacaoService
from services.kanban_service import KanbanService, PhaseTransitionError
from services.automacao_service import AutomacaoService




app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or os.urandom(10).hex()
app.permanent_session_lifetime = timedelta(days=7)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
AUTHORIZATION_BASE_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPE = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# Configuração do Scheduler
scheduler = APScheduler()

def job_recalcular_remuneracao():
    """Tarefa agendada para rodar diariamente."""
    print(f"[{dt.now()}] Iniciando recalculo automatico de remuneracao...")
    from datetime import datetime as dt
    from services.remuneracao import calcular_metricas_mensais
    try:
        ProjetoParticipacaoService.sincronizar_remuneracao(dt.now().month, dt.now().year)
        calcular_metricas_mensais(dt.now().month, dt.now().year)
        print("Recalculo automatico concluido com sucesso.")

    except Exception as e:
        print(f"Erro no agendamento: {e}")

# Inicia o scheduler
scheduler.init_app(app)
scheduler.start()

# Agenda a tarefa para todos os dias à meia-noite (00:00)
@scheduler.task('cron', id='do_remuneracao_daily', hour=0, minute=0)
def daily_remuneration_job():
    job_recalcular_remuneracao()

@scheduler.task('cron', id='do_automacoes_project_date_daily', hour=1, minute=0)
def daily_automacoes_project_date_job():
    """Verifica gatilhos baseados em data do projeto."""
    print(f"[{dt.now()}] Verificando gatilhos de data de projeto nas automações...")
    try:
        with Session() as db:
            service = AutomacaoService(db)
            service.check_project_date_triggers()
        print("Verificação de gatilhos de data concluída.")
    except Exception as e:
        print(f"Erro na verificação de gatilhos de data: {e}")


def check_session(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "nome" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


def check_access(roles):
    """Decorator para verificar cargo do usuário."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_role = session.get("funcao", "").strip()
            user_posicao = session.get("posicao", "").strip()
            
            import unicodedata
            # Se for Gerência, Sócio ou Coordenador via posição, concede acesso a quase tudo
            _pos_norm = unicodedata.normalize('NFC', user_posicao.lower())
            is_high_level = any(
                unicodedata.normalize('NFC', r.lower()) == _pos_norm
                for r in ["Gerência", "Sócio", "Coordenador"]
            )
            
            # Verifica se o cargo solicitado está na lista ou se é Gerência/Sócio
            # Normaliza NFC para evitar diferenças de composição Unicode (ex: á vs a+acento)
            import unicodedata
            _user_norm = unicodedata.normalize('NFC', user_role.lower())
            if not is_high_level and not any(
                unicodedata.normalize('NFC', role.lower()) == _user_norm
                for role in roles
            ):
                print(f"[check_access] BLOQUEADO: user_role={user_role!r} user_posicao={user_posicao!r} roles={roles}")
                return render_template("index.html", error="Acesso restrito.")
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ─── HELPERS ────────────────────────────────────────────────────────────────

# ── Helpers: Gestão de Entregas Operação ─────────────────────────────────────

_ENTREGAS_ACCOUNT_TPL = [
    {"nome": "relatorio_account",        "tipo": "account", "meta": 1, "entregues": 0},
    {"nome": "planner_monday",           "tipo": "account", "meta": 4, "entregues": 0},
    {"nome": "csat_checkin",             "tipo": "account", "meta": 4, "entregues": 0},
    {"nome": "forecasting",              "tipo": "account", "meta": 1, "entregues": 0},
]

_ENTREGAS_GT_TPL = [
    {"nome": "kpis",                    "tipo": "gt", "meta": 1, "entregues": 0},
    {"nome": "plano_de_midia",          "tipo": "gt", "meta": 1, "entregues": 0},
    {"nome": "documento_de_otimizacao", "tipo": "gt", "meta": 4, "entregues": 0},
    {"nome": "relatorio_gt",            "tipo": "gt", "meta": 1, "entregues": 0},
]


def _build_entregas_op_list(responsavel):
    if responsavel == "account":
        return [dict(e) for e in _ENTREGAS_ACCOUNT_TPL]
    if responsavel == "gt":
        return [dict(e) for e in _ENTREGAS_GT_TPL]
    if responsavel == "cientista":
        seen, result = set(), []
        # Para cientista, unificamos os relatórios em um só 'relatorio_mensal'
        base_list = [dict(e) for e in _ENTREGAS_ACCOUNT_TPL] + [dict(e) for e in _ENTREGAS_GT_TPL]
        for e in base_list:
            nome = e["nome"]
            if nome in ("relatorio_account", "relatorio_gt"):
                nome = "relatorio_mensal"
            
            if nome not in seen:
                seen.add(nome)
                e["nome"] = nome
                e["tipo"] = "CIENTISTA"
                result.append(e)
        return result
    return []


def _build_entrega_op_entry(projeto_id, cliente_nome, responsavel):
    entry = {
        "cliente": cliente_nome,
        "projeto_id": str(projeto_id),
        "responsavel": responsavel,
        "link_relatorio": "",
        "entregas": _build_entregas_op_list(responsavel),
    }
    # link_kpi: apenas GT e Cientista (kpis é uma entrega de GT)
    if responsavel in ("gt", "cientista"):
        entry["link_kpi"] = ""
    # link_forecast: Account (forecasting) e Cientista
    if responsavel in ("account", "cientista"):
        entry["link_forecast"] = ""
    return entry


def _update_entrega_op_entregues(entregas_list, projeto_id, cliente_nome, responsavel, nome_entrega, tipo_entrega, valor):
    entregas_list = list(entregas_list or [])
    idx = next(
        (i for i, e in enumerate(entregas_list) if str(e.get("projeto_id")) == str(projeto_id)),
        None
    )
    if idx is None:
        entry = _build_entrega_op_entry(projeto_id, cliente_nome, responsavel)
        entregas_list.append(entry)
        idx = len(entregas_list) - 1

    entry = dict(entregas_list[idx])
    itens = [dict(e) for e in (entry.get("entregas") or [])]
    REL_ALIASES = {"relatorio_mensal", "relatorio_gt", "relatorio_account"}
    for item in itens:
        is_match = False
        if responsavel == "cientista":
            nome_item = item.get("nome")
            # Unifica nomes de relatórios para cientistas no match
            if nome_item in ("relatorio_account", "relatorio_gt"):
                nome_item = "relatorio_mensal"

            target_nome = nome_entrega
            if target_nome in ("relatorio_account", "relatorio_gt"):
                target_nome = "relatorio_mensal"

            if nome_item == target_nome:
                is_match = True
                item["tipo"] = "CIENTISTA" # Normaliza legado
                item["nome"] = nome_item   # Normaliza nome se necessário
        else:
            nome_item = item.get("nome")
            target_nome = nome_entrega
            # 'relatorio_mensal' (frontend) é alias de 'relatorio_gt'/'relatorio_account' (template novo)
            if nome_item in REL_ALIASES and target_nome in REL_ALIASES:
                nome_match = True
            else:
                nome_match = (nome_item == target_nome)

            # Aceita item legado com tipo='CIENTISTA' quando o vínculo virou gt/account
            tipo_item = item.get("tipo")
            tipo_match = (tipo_item == tipo_entrega) or (tipo_item == "CIENTISTA")

            if nome_match and tipo_match:
                is_match = True

        if is_match:
            item["entregues"] = max(0, min(int(valor), item.get("meta", 1)))
            break
    entry["entregas"] = itens
    entregas_list[idx] = entry
    return entregas_list


def _update_entrega_op_links(entregas_list, projeto_id, cliente_nome="", responsavel_hint="",
                             link_relatorio=None, link_kpi=None, link_forecast=None):
    entregas_list = list(entregas_list or [])
    idx = next(
        (i for i, e in enumerate(entregas_list) if str(e.get("projeto_id")) == str(projeto_id)),
        None
    )
    if idx is None:
        if not responsavel_hint:
            return entregas_list
        entry = _build_entrega_op_entry(projeto_id, cliente_nome, responsavel_hint)
        entregas_list.append(entry)
        idx = len(entregas_list) - 1

    entry = {k: (dict(v) if isinstance(v, dict) else v) for k, v in entregas_list[idx].items()}
    responsavel = entry.get("responsavel", "") or responsavel_hint
    if link_relatorio is not None:
        entry["link_relatorio"] = link_relatorio
    if link_kpi is not None and responsavel in ("gt", "cientista"):
        entry["link_kpi"] = link_kpi
    if link_forecast is not None and responsavel in ("account", "cientista"):
        entry["link_forecast"] = link_forecast
    entregas_list[idx] = entry
    return entregas_list


# ── Helpers: Gestão de Entregas Criativas ────────────────────────────────────

def get_entregas_by_projeto(entregas_list, projeto_id):
    """Retorna o objeto de entrega para um projeto_id dentro do array JSONB."""
    for e in (entregas_list or []):
        if str(e.get("projeto_id")) == str(projeto_id):
            return e
    return None


def _build_entrega_entry(projeto_id, cliente_nome):
    """Cria um objeto de entrega zerado para um projeto."""
    return {
        "cliente": cliente_nome,
        "projeto_id": str(projeto_id),
        "link_criativos": "",
        "criativos": {"contratados": 0, "entregues": 0},
        "videos": {"contratados": 0, "entregues": 0},
        "lp": {"contratados": 0, "entregues": 0},
    }


def _update_entrega_field(entregas_list, projeto_id, cliente_nome, categoria, campo, valor):
    """Atualiza contratados ou entregues de uma categoria no array JSONB sem sobrescrever o todo."""
    entregas_list = list(entregas_list or [])
    idx = next(
        (i for i, e in enumerate(entregas_list) if str(e.get("projeto_id")) == str(projeto_id)),
        None
    )
    if idx is None:
        entry = _build_entrega_entry(projeto_id, cliente_nome)
        entregas_list.append(entry)
        idx = len(entregas_list) - 1

    # Deep-copy da entrada para acionar detecção de mutação do SQLAlchemy
    entry = {k: (dict(v) if isinstance(v, dict) else v) for k, v in entregas_list[idx].items()}
    cat = entry.get(categoria, {"contratados": 0, "entregues": 0})
    cat = dict(cat)
    cat[campo] = max(0, int(valor))
    entry[categoria] = cat
    entregas_list[idx] = entry
    return entregas_list


def update_contratados(entregas_list, projeto_id, cliente_nome, categoria, valor):
    """Atualiza a quantidade contratada para uma categoria (uso do Coordenador)."""
    return _update_entrega_field(entregas_list, projeto_id, cliente_nome, categoria, "contratados", valor)


def update_entregues(entregas_list, projeto_id, cliente_nome, categoria, valor):
    """Atualiza a quantidade entregue para uma categoria (uso do Time Operacional)."""
    return _update_entrega_field(entregas_list, projeto_id, cliente_nome, categoria, "entregues", valor)


def update_link_criativo(entregas_list, projeto_id, cliente_nome, link):
    """Atualiza o link de criativos para um projeto no array JSONB."""
    entregas_list = list(entregas_list or [])
    idx = next(
        (i for i, e in enumerate(entregas_list) if str(e.get("projeto_id")) == str(projeto_id)),
        None
    )
    if idx is None:
        entry = _build_entrega_entry(projeto_id, cliente_nome)
        entry["link_criativos"] = link
        entregas_list.append(entry)
    else:
        entry = {k: (dict(v) if isinstance(v, dict) else v) for k, v in entregas_list[idx].items()}
        entry["link_criativos"] = link
        entregas_list[idx] = entry
    return entregas_list


def _get_or_create_entrega_record(db, email, mes, ano):
    """
    Busca ou cria o registro em investidores_metricas_mensais_novo para email/mês/ano.
    Se não existir ainda (mês sem cálculo de métricas), cria registro mínimo —
    as colunas financeiras serão preenchidas pelo scheduler quando necessário.
    """
    record = db.query(MetricaMensal).filter_by(
        email_investidor=email, mes=mes, ano=ano
    ).with_for_update().first()
    if record is None:
        record = MetricaMensal(
            email_investidor=email,
            mes=mes,
            ano=ano,
            entregas_criativos=[],
            entregas_operacao=[],
        )
        db.add(record)
        db.flush()
    return record

# ─────────────────────────────────────────────────────────────────────────────

def _recalcular_mrr_por_entregas(db, record):
    """
    Recalcula os campos de MRR no MetricaMensal após o registro de uma entrega.
    Garante que fixo_mrr_entrega, fixo_mrr_atual, fixo_churn_atual e
    fixo_mrr_projeto_total fiquem sempre consistentes entre si.
    O banco usa fixo_mrr_atual (entregue - churn) para todas as fórmulas GENERATED.
    Usa a sessão do caller (db) para evitar sessões extras e N+1 queries.
    """
    from decimal import Decimal

    is_criativo = record.cargo in ("Designer", "WebDesigner", "Webdesigner")
    entregas = record.entregas_criativos if is_criativo else record.entregas_operacao
    entregas = entregas or []
    entregas_map = {str(p.get("projeto_id")): p for p in entregas if p.get("projeto_id")}

    mes_atual_str = f"{record.ano}-{record.mes:02d}"
    hist = record.historico_projetos or []

    total_mrr_entregue = Decimal("0")
    mrr_portfolio_total = Decimal("0")
    churn_calculado = Decimal("0")
    novos_detalhes = []

    # Batch query: busca todos os vínculos e projetos em 2 queries
    from models import Projeto
    from sqlalchemy import or_, and_, extract
    todos_vinculos = db.query(InvestidorProjeto).filter(
        InvestidorProjeto.email_investidor == record.email_investidor
    ).all()

    # Batch query projetos (elimina N+1)
    proj_ids = list({v.pipefy_id_projeto for v in todos_vinculos})
    projs_map = {}
    if proj_ids:
        projs_list = db.query(Projeto).filter(Projeto.pipefy_id.in_(proj_ids)).all()
        projs_map = {p.pipefy_id: p for p in projs_list}

    usd_rate = None

    for v in todos_vinculos:
        pid = str(v.pipefy_id_projeto)
        proj = projs_map.get(v.pipefy_id_projeto)
        moeda_proj = str(proj.moeda).strip().upper() if proj and proj.moeda else "BRL"

        if moeda_proj == "USD":
            from services.currency import CurrencyService
            if usd_rate is None:
                usd_rate = CurrencyService.get_usd_to_brl_rate()

        # FEE COMPLETO — para mrr_portfolio_total (flag e teto)
        fee_full = Decimal(str(v.fee_projeto or 0))
        if v.cientista:
            fee_full *= Decimal("1.5")
        if moeda_proj == "USD" and usd_rate:
            fee_full *= usd_rate
        fee_full = fee_full.quantize(Decimal("0.01"))

        # FEE PROPORCIONAL — para MRR entregue e churn (dias trabalhados no mês)
        proj_hist = next((h for h in hist if str(h.get("projeto_id")) == pid), None)
        if proj_hist and "valor_proporcional" in proj_hist:
            fee = Decimal(str(proj_hist["valor_proporcional"]))
            if moeda_proj == "USD" and usd_rate:
                fee *= usd_rate
            fee = fee.quantize(Decimal("0.01"))
        else:
            fee = fee_full

        eh_churn_atual_proj = False
        if not v.active:
            if v.inactivated_at and v.inactivated_at.strftime("%Y-%m") == mes_atual_str:
                eh_churn_atual_proj = True

        if v.active or eh_churn_atual_proj:
            mrr_portfolio_total += fee_full

            detalhe = {
                "id": v.pipefy_id_projeto,
                "nome": v.nome_projeto,
                "moeda": moeda_proj,
                "cientista": bool(v.cientista),
                "ativo": v.active,
                "fee": float(fee_full)
            }

            if eh_churn_atual_proj:
                churn_calculado += fee
                detalhe["churned"] = True
                detalhe["data_churn"] = v.inactivated_at.strftime("%d/%m/%Y")

            novos_detalhes.append(detalhe)

            p = entregas_map.get(pid)
            if record.ano == 2026 and record.mes in (2, 3):
                progresso = Decimal("0")
            else:
                if p:
                    if is_criativo:
                        c_c = p.get("criativos", {}).get("contratados", 0)
                        c_e = p.get("criativos", {}).get("entregues", 0)
                        v_c = p.get("videos", {}).get("contratados", 0)
                        v_e = p.get("videos", {}).get("entregues", 0)
                        l_c = p.get("lp", {}).get("contratados", 0)
                        l_e = p.get("lp", {}).get("entregues", 0)
                        total_meta = c_c + v_c + l_c
                        total_entregues = min(c_e, c_c) + min(v_e, v_c) + min(l_e, l_c)
                        progresso = Decimal(str(total_entregues / total_meta)) if total_meta > 0 else Decimal("1")
                    else:
                        itens = p.get("entregas", [])
                        if not itens:
                            progresso = Decimal("0")
                        else:
                            from decimal import ROUND_HALF_UP
                            peso_por_tipo = Decimal("100.0") / Decimal(str(len(itens)))
                            sum_progresso = Decimal("0")
                            for item in itens:
                                meta = Decimal(str(item.get("meta", 0)))
                                entregues = min(Decimal(str(item.get("entregues", 0))), meta)
                                if meta > 0:
                                    sum_progresso += (entregues / meta) * peso_por_tipo
                            sum_progresso = sum_progresso.to_integral_value(rounding=ROUND_HALF_UP)
                            progresso = sum_progresso / Decimal("100.0")
                else:
                    progresso = Decimal("1") if is_criativo else Decimal("0")

            total_mrr_entregue += fee * progresso

    record.fixo_mrr_entrega = total_mrr_entregue
    record.fixo_mrr_atual = max(Decimal("0"), total_mrr_entregue - churn_calculado)
    record.fixo_churn_atual = churn_calculado
    record.fixo_mrr_projeto_total = mrr_portfolio_total
    record.detalhes = {"produtos": novos_detalhes}

    flag_modified(record, "fixo_mrr_entrega")
    flag_modified(record, "fixo_mrr_atual")
    flag_modified(record, "fixo_churn_atual")
    flag_modified(record, "fixo_mrr_projeto_total")
    flag_modified(record, "detalhes")


# ─── HELPERS TABELA OPERACAO (UNICA TABELA DE ENTREGAS) ──────────────────────

def _operacao_empty_json():
    """Estrutura padrão do JSON entregas."""
    return {
        "plano_midia":        {"budget_total": 0, "planos": []},
        "otimizacoes":        [],
        "forecasting":        {"link": ""},
        "kpis":               {"link": ""},
        "checkin_semanal":    [],
        "relatorio_mensal":   {"link": ""},
        "relatorio_account":  {"link": ""},
        "relatorio_gt":       {"link": ""},
        "metas":              {},
        "tarefas_semanais":   [],
    }


def _operacao_get_snapshot(pipefy_id, mes, ano):
    """Lê plataforma_geral.operacao.entregas para projeto+mes+ano. Retorna dict ou None."""
    try:
        with Session() as db:
            row = db.execute(text(
                "SELECT entregas FROM plataforma_geral.operacao "
                "WHERE id_projeto = :id AND mes = :mes AND ano = :ano LIMIT 1"
            ), {"id": str(pipefy_id), "mes": int(mes), "ano": int(ano)}).first()
            if not row or row.entregas is None:
                return None
            if isinstance(row.entregas, dict):
                return row.entregas
            return json.loads(row.entregas)
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[operacao_get] {e}")
        return None


def _infer_entregas_op_responsavel(db, email, pipefy_id, responsavel_hint=""):
    if responsavel_hint in ("account", "gt", "cientista"):
        hint = responsavel_hint
    else:
        hint = ""

    vinculo = db.query(InvestidorProjeto).filter_by(
        email_investidor=email, pipefy_id_projeto=pipefy_id
    ).first()
    if vinculo and vinculo.cientista:
        return "cientista"

    if hint in ("account", "gt"):
        return hint

    investidor = db.query(Investidor).filter(Investidor.email.ilike(email)).first()
    if investidor and investidor.funcao in ("Account", "Coordenador de CX"):
        return "account"
    return "gt"


def _sync_snapshot_links_from_entregas_op(db, pipefy_id, mes, ano, responsavel,
                                          link_relatorio=None, link_kpi=None, link_forecast=None):
    """Espelha links salvos na visão consolidada para o snapshot oficial do projeto."""
    updates = []
    if link_kpi is not None:
        updates.append(("kpis", {"link": link_kpi or ""}))
    if link_forecast is not None:
        updates.append(("forecasting", {"link": link_forecast or ""}))
    if link_relatorio is not None:
        if responsavel == "account":
            section = "relatorio_account"
        elif responsavel == "gt":
            section = "relatorio_gt"
        else:
            section = "relatorio_mensal"
        updates.append((section, {"link": link_relatorio or ""}))

    for section_key, payload in updates:
        OperacaoSnapshotService.update_section(
            db, pipefy_id, int(mes), int(ano), section_key, payload
        )


def _apply_legacy_links_to_snapshot_dict(snap, entry, responsavel):
    """Copia links antigos de entregas_operacao para o snapshot em memória, se faltarem."""
    changed = False

    legacy_kpi = entry.get("link_kpi") or ""
    if legacy_kpi and not ((snap.get("kpis") or {}).get("link")):
        snap["kpis"] = dict(snap.get("kpis") or {})
        snap["kpis"]["link"] = legacy_kpi
        changed = True

    legacy_forecast = entry.get("link_forecast") or ""
    if legacy_forecast and not ((snap.get("forecasting") or {}).get("link")):
        snap["forecasting"] = dict(snap.get("forecasting") or {})
        snap["forecasting"]["link"] = legacy_forecast
        changed = True

    legacy_relatorio = entry.get("link_relatorio") or ""
    has_report = (
        (snap.get("relatorio_mensal") or {}).get("link") or
        (snap.get("relatorio_account") or {}).get("link") or
        (snap.get("relatorio_gt") or {}).get("link")
    )
    if legacy_relatorio and not has_report:
        if responsavel == "account":
            section = "relatorio_account"
        elif responsavel == "gt":
            section = "relatorio_gt"
        else:
            section = "relatorio_mensal"
        snap[section] = dict(snap.get(section) or {})
        snap[section]["link"] = legacy_relatorio
        changed = True

    return changed


def _operacao_save_section(pipefy_id, mes, ano, section_key, data, append=False, nome=None):
    """
    Salva uma seção do JSON entregas na tabela plataforma_geral.operacao.
    Usa engine.begin() para transação auto-commit confiável.
    Verifica existência da linha após o commit.
    """
    print(f"[_operacao_save_section] pipefy_id={pipefy_id} mes={mes} ano={ano} section={section_key} append={append}")
    try:
        # Validar parâmetros
        if pipefy_id is None or mes is None or ano is None:
            print(f"[operacao] ERRO: parâmetros inválidos pipefy_id={pipefy_id} mes={mes} ano={ano}")
            return False

        # Buscar nome do projeto
        if nome is None:
            with Session() as ndb:
                proj = ndb.query(Projeto).filter_by(pipefy_id=pipefy_id).first()
                nome = proj.nome if proj else ""

        id_str = str(pipefy_id)
        mes_int = int(mes)
        ano_int = int(ano)

        # engine.begin() abre transação e dá commit automático no exit (ou rollback se exception)
        with engine.begin() as conn:
            row = conn.execute(text(
                "SELECT id, entregas FROM plataforma_geral.operacao "
                "WHERE id_projeto = :id AND mes = :mes AND ano = :ano LIMIT 1"
            ), {"id": id_str, "mes": mes_int, "ano": ano_int}).mappings().first()

            if row:
                print(f"[operacao] linha existe id={row['id']} -> UPDATE")
                current_raw = row["entregas"]
                if isinstance(current_raw, dict):
                    current = current_raw
                elif current_raw:
                    current = json.loads(current_raw)
                else:
                    current = _operacao_empty_json()

                if append:
                    lst = list(current.get(section_key) or [])
                    lst.append(data)
                    current[section_key] = lst
                else:
                    current[section_key] = data

                conn.execute(text(
                    "UPDATE plataforma_geral.operacao "
                    "SET entregas = CAST(:ent AS jsonb) WHERE id = :rid"
                ), {"ent": json.dumps(current, ensure_ascii=False), "rid": row["id"]})
            else:
                print(f"[operacao] linha NÃO existe -> INSERT")
                full = _operacao_empty_json()
                if append:
                    full[section_key] = [data]
                else:
                    full[section_key] = data

                conn.execute(text(
                    "INSERT INTO plataforma_geral.operacao "
                    "(mes, ano, nome, id_projeto, entregas) "
                    "VALUES (:mes, :ano, :nome, :id, CAST(:ent AS jsonb))"
                ), {"mes": mes_int, "ano": ano_int, "nome": nome or "",
                    "id": id_str, "ent": json.dumps(full, ensure_ascii=False)})

        # Verificar que foi persistido
        with engine.connect() as conn2:
            check = conn2.execute(text(
                "SELECT id FROM plataforma_geral.operacao "
                "WHERE id_projeto = :id AND mes = :mes AND ano = :ano LIMIT 1"
            ), {"id": id_str, "mes": mes_int, "ano": ano_int}).first()

            if check:
                print(f"[operacao] OK CONFIRMADO id={check[0]} projeto={pipefy_id} mes={mes} ano={ano}")
                return True
            else:
                print(f"[operacao] FALHA: linha nao encontrada apos commit!")
                return False
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[operacao] ERRO save: {e}")
        return False


def _sync_metrica_entregas_operacao(email, pipefy_id, mes, ano):
    """
    Lê o snapshot da operacao e atualiza MetricaMensal.entregas_operacao
    para o usuário (entregues por delivery_type + links). Recalcula MRR.
    Protege meses fechados.
    Sincroniza TODOS os tipos de entrega que existam no snapshot,
    independente do cargo do usuário.
    """
    try:
        from datetime import datetime as _dt

        snap = _operacao_get_snapshot(pipefy_id, mes, ano)
        if not snap:
            print(f"[metrica sync] sem snapshot para projeto={pipefy_id} {mes}/{ano}")
            return

        with Session() as db:
            investidor = db.query(Investidor).filter(Investidor.email.ilike(email)).first()
            if not investidor:
                print(f"[metrica sync] investidor não encontrado: {email}")
                return

            metrica = db.query(MetricaMensal).filter_by(
                email_investidor=email, mes=mes, ano=ano
            ).first()
            if not metrica:
                print(f"[metrica sync] MetricaMensal não encontrada: {email} {mes}/{ano}")
                return

            lista = list(metrica.entregas_operacao or [])
            entry = next((e for e in lista if str(e.get("projeto_id")) == str(pipefy_id)), None)
            entry_created = False

            if not entry:
                # Se não existe, precisamos criar a entrada baseada no vínculo (checar se é cientista)
                vinculo = db.query(InvestidorProjeto).filter_by(
                    email_investidor=email, pipefy_id_projeto=pipefy_id
                ).first()
                if not vinculo:
                    print(f"[metrica sync] vínculo não encontrado para {email} projeto={pipefy_id}")
                    return
                
                # Determinar o 'responsavel' hint para o build
                if vinculo.cientista:
                    hint = "cientista"
                else:
                    hint = "account" if investidor.funcao in ("Account", "Coordenador de CX") else "gt"
                
                # Buscar nome do projeto
                proj_name = vinculo.nome_projeto or ""
                if not proj_name:
                    p_ativo = db.query(Projeto).filter_by(pipefy_id=pipefy_id, status='Ativo').first()
                    proj_name = p_ativo.nome if p_ativo else f"Projeto {pipefy_id}"

                entry = _build_entrega_op_entry(pipefy_id, proj_name, hint)
                lista.append(entry)
                metrica.entregas_operacao = lista
                entry_created = True
                # Não retornamos, continuamos para preencher os counts no novo entry

            # Verificar se o template da entry condiz com o cargo atual
            _vinculo = db.query(InvestidorProjeto).filter_by(
                email_investidor=email, pipefy_id_projeto=pipefy_id
            ).first()
            if _vinculo:
                if _vinculo.cientista:
                    _expected_resp = "cientista"
                else:
                    _expected_resp = "account" if investidor.funcao in ("Account", "Coordenador de CX") else "gt"
                _current_resp = entry.get("responsavel", "")
                if _current_resp != _expected_resp:
                    _existing = {e.get("nome"): e.get("entregues", 0) for e in entry.get("entregas", [])}
                    entry["responsavel"] = _expected_resp
                    entry["entregas"] = _build_entregas_op_list(_expected_resp)
                    for _e in entry["entregas"]:
                        if _e["nome"] in _existing:
                            _e["entregues"] = _existing[_e["nome"]]
                    _template_changed = True
                else:
                    _template_changed = False
            else:
                _template_changed = False

            # Extrair contagens do snapshot — todos os tipos, sem filtrar por cargo
            plano_planos     = (snap.get("plano_midia") or {}).get("planos") or []
            otims            = snap.get("otimizacoes") or []
            checkins         = snap.get("checkin_semanal") or []
            kpis_link        = (snap.get("kpis") or {}).get("link") or ""
            forecasting_link = (snap.get("forecasting") or {}).get("link") or ""
            relatorio_link   = (snap.get("relatorio_mensal") or {}).get("link") or ""
            relatorio_acc_link = (snap.get("relatorio_account") or {}).get("link") or ""
            relatorio_gt_link  = (snap.get("relatorio_gt") or {}).get("link") or ""

            # Contagens para TODOS os tipos de entrega
            # Forecasting: concluído se houver link OU se a meta do snapshot (metas) estiver marcada como concluída
            goal_snap = snap.get("metas") or {}
            is_forecast_done = 1 if (forecasting_link or goal_snap.get("concluida")) else 0

            counts = {
                "plano_de_midia":          1 if plano_planos else 0,
                "documento_de_otimizacao": min(len(otims), 4),
                "kpis":                    1 if kpis_link else 0,
                "csat_checkin":            min(len(checkins), 4),
                "forecasting":             is_forecast_done,
                "relatorio_mensal":        1 if (relatorio_link or relatorio_acc_link or relatorio_gt_link) else 0,
                "relatorio_account":       1 if (relatorio_acc_link or relatorio_link) else 0,
                "relatorio_gt":            1 if (relatorio_gt_link or relatorio_link) else 0,
            }

            responsavel_entry = entry.get("responsavel", "")
            links = {}
            if responsavel_entry in ("gt", "cientista") or entry.get("link_kpi"):
                links["link_kpi"] = kpis_link
            if responsavel_entry in ("account", "cientista") or entry.get("link_forecast"):
                links["link_forecast"] = forecasting_link
            links["link_relatorio"] = relatorio_link or relatorio_acc_link or relatorio_gt_link

            # Contabilizar tarefas semanais (planner_monday)
            if "tarefas_semanais" in snap:
                count_semanal = len(snap["tarefas_semanais"])
            else:
                # Fallback para tabela antiga — SAVEPOINT protege a sessão
                count_semanal = 0
                try:
                    nested = db.begin_nested()
                    tarefas_db = db.query(OperacaoTarefa).filter_by(
                        projeto_pipefy_id=pipefy_id, tipo="semanal", ano=ano
                    ).all()
                    for t in tarefas_db:
                        try:
                            if t.referencia and "-W" in t.referencia:
                                y, w = map(int, t.referencia.split("-W"))
                                d = _dt.fromisocalendar(y, w, 1)
                                if d.month == mes: count_semanal += 1
                        except Exception: pass
                    nested.commit()
                except Exception:
                    try:
                        nested.rollback()
                    except Exception:
                        pass
                    print(f"[metrica sync] tabela operacao_tarefas indisponível, ignorando fallback")
                    count_semanal = 0
            counts["planner_monday"] = min(count_semanal, 4)

            # Preservar contagens maiores registradas via /criativa (MetricaMensal)
            _existing = {e.get("nome"): e.get("entregues", 0) for e in entry.get("entregas", [])}
            _metas_corretas = {tpl["nome"]: tpl["meta"] for tpl in _ENTREGAS_ACCOUNT_TPL + _ENTREGAS_GT_TPL}
            for _nome in list(counts.keys()):
                _existing_val = _existing.get(_nome, 0)
                _meta_val = _metas_corretas.get(_nome, 4)
                counts[_nome] = min(max(counts[_nome], _existing_val), _meta_val)

            changed = entry_created or _template_changed
            for ent in entry.get("entregas", []):
                n = ent.get("nome")
                if n in counts and ent.get("entregues") != counts[n]:
                    ent["entregues"] = counts[n]
                    changed = True
                meta_correta = _metas_corretas.get(n)
                if meta_correta and ent.get("meta") != meta_correta:
                    ent["meta"] = meta_correta
                    changed = True
            for k, v in links.items():
                if entry.get(k) != v:
                    entry[k] = v
                    changed = True

            if changed:
                flag_modified(metrica, "entregas_operacao")
                _recalcular_mrr_por_entregas(db, metrica)
                db.commit()
                print(f"[metrica sync] OK {email} projeto={pipefy_id} counts={counts}")
            else:
                print(f"[metrica sync] sem mudancas {email} projeto={pipefy_id}")
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[metrica sync] ERRO: {e}")


def _sync_entregas_operacao_periodo(email, mes, ano):
    """Concilia snapshots do projeto com entregas_operacao para um usuário/mês."""
    project_ids = set()
    try:
        with Session() as db:
            record = db.query(MetricaMensal).filter_by(
                email_investidor=email, mes=mes, ano=ano
            ).first()

            if record and record.entregas_operacao:
                for entry in record.entregas_operacao or []:
                    pid = entry.get("projeto_id")
                    if not pid:
                        continue
                    project_ids.add(str(pid))

                    # Recupera links legados que foram salvos só em entregas_operacao.
                    legacy_relatorio = entry.get("link_relatorio") or None
                    legacy_kpi = entry.get("link_kpi") or None
                    legacy_forecast = entry.get("link_forecast") or None
                    if legacy_relatorio or legacy_kpi or legacy_forecast:
                        responsavel = _infer_entregas_op_responsavel(
                            db, email, int(pid), entry.get("responsavel", "")
                        )
                        _sync_snapshot_links_from_entregas_op(
                            db, int(pid), mes, ano, responsavel,
                            link_relatorio=legacy_relatorio,
                            link_kpi=legacy_kpi,
                            link_forecast=legacy_forecast,
                        )

            vinculos = db.query(InvestidorProjeto.pipefy_id_projeto).filter_by(
                email_investidor=email
            ).all()
            for v in vinculos:
                pid = str(v.pipefy_id_projeto)
                if _operacao_get_snapshot(pid, mes, ano):
                    project_ids.add(pid)

            db.commit()

        for pid in project_ids:
            _sync_metrica_entregas_operacao(email, int(pid), int(mes), int(ano))
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[metrica sync periodo] ERRO: {e}")


def _sync_entregas_operacao_periodo_fast(email, mes, ano):
    """Concilia entregas_operacao em lote, evitando uma sincronizacao por projeto."""
    try:
        with Session() as db:
            investidor = db.query(Investidor).filter(Investidor.email.ilike(email)).first()
            if not investidor:
                return

            vinculos = db.query(InvestidorProjeto).filter_by(
                email_investidor=email
            ).all()
            pid_values = list({str(v.pipefy_id_projeto) for v in vinculos if v.pipefy_id_projeto})
            if not pid_values:
                return

            rows = db.execute(text(
                "SELECT id, id_projeto, nome, entregas FROM plataforma_geral.operacao "
                "WHERE id_projeto = ANY(:ids) AND mes = :mes AND ano = :ano"
            ), {"ids": pid_values, "mes": int(mes), "ano": int(ano)}).mappings().all()
            if not rows:
                return

            record = db.query(MetricaMensal).filter_by(
                email_investidor=email, mes=int(mes), ano=int(ano)
            ).first()
            if record is None:
                record = _get_or_create_entrega_record(db, email, int(mes), int(ano))

            lista = list(record.entregas_operacao or [])
            entries_by_pid = {
                str(e.get("projeto_id")): e
                for e in lista
                if e.get("projeto_id")
            }
            vinculos_by_pid = {str(v.pipefy_id_projeto): v for v in vinculos}

            tarefas_por_pid = defaultdict(int)
            try:
                nested_t = db.begin_nested()
                tarefas_db = db.query(OperacaoTarefa).filter(
                    OperacaoTarefa.projeto_pipefy_id.in_([int(pid) for pid in pid_values]),
                    OperacaoTarefa.tipo == "semanal",
                    OperacaoTarefa.ano == int(ano),
                ).all()
                for tarefa in tarefas_db:
                    try:
                        if tarefa.referencia and "-W" in tarefa.referencia:
                            y, w = map(int, tarefa.referencia.split("-W"))
                            d = dt.fromisocalendar(y, w, 1)
                            if d.month == int(mes):
                                tarefas_por_pid[str(tarefa.projeto_pipefy_id)] += 1
                    except Exception:
                        pass
                nested_t.commit()
            except Exception:
                try:
                    nested_t.rollback()
                except Exception:
                    pass
                tarefas_por_pid = defaultdict(int)

            metas_corretas = {
                tpl["nome"]: tpl["meta"]
                for tpl in _ENTREGAS_ACCOUNT_TPL + _ENTREGAS_GT_TPL
            }
            changed = False

            for row in rows:
                pid = str(row["id_projeto"])
                vinculo = vinculos_by_pid.get(pid)
                if not vinculo:
                    continue

                snap = row["entregas"] if isinstance(row["entregas"], dict) else (
                    json.loads(row["entregas"]) if row["entregas"] else {}
                )

                entry = entries_by_pid.get(pid)
                if not entry:
                    if vinculo.cientista:
                        responsavel = "cientista"
                    else:
                        responsavel = "account" if investidor.funcao in ("Account", "Coordenador de CX") else "gt"
                    proj_name = vinculo.nome_projeto or row["nome"] or f"Projeto {pid}"
                    entry = _build_entrega_op_entry(pid, proj_name, responsavel)
                    lista.append(entry)
                    entries_by_pid[pid] = entry
                    changed = True

                responsavel = _infer_entregas_op_responsavel(
                    db, email, int(pid), entry.get("responsavel", "")
                )
                if _apply_legacy_links_to_snapshot_dict(snap, entry, responsavel):
                    db.execute(text(
                        "UPDATE plataforma_geral.operacao "
                        "SET entregas = CAST(:ent AS jsonb) WHERE id = :rid"
                    ), {"ent": json.dumps(snap, ensure_ascii=False), "rid": row["id"]})
                    changed = True

                plano_planos = (snap.get("plano_midia") or {}).get("planos") or []
                otims = snap.get("otimizacoes") or []
                checkins = snap.get("checkin_semanal") or []
                kpis_link = (snap.get("kpis") or {}).get("link") or ""
                forecasting_link = (snap.get("forecasting") or {}).get("link") or ""
                relatorio_link = (snap.get("relatorio_mensal") or {}).get("link") or ""
                relatorio_acc_link = (snap.get("relatorio_account") or {}).get("link") or ""
                relatorio_gt_link = (snap.get("relatorio_gt") or {}).get("link") or ""
                goal_snap = snap.get("metas") or {}

                _snap_monday = len(snap["tarefas_semanais"]) if "tarefas_semanais" in snap else tarefas_por_pid.get(pid, 0)

                counts = {
                    "plano_de_midia": 1 if plano_planos else 0,
                    "documento_de_otimizacao": min(len(otims), 4),
                    "kpis": 1 if kpis_link else 0,
                    "csat_checkin": min(len(checkins), 4),
                    "forecasting": 1 if (forecasting_link or goal_snap.get("concluida")) else 0,
                    "relatorio_mensal": 1 if (relatorio_link or relatorio_acc_link or relatorio_gt_link) else 0,
                    "relatorio_account": 1 if (relatorio_acc_link or relatorio_link) else 0,
                    "relatorio_gt": 1 if (relatorio_gt_link or relatorio_link) else 0,
                    "planner_monday": min(_snap_monday, 4),
                }

                # Preservar contagens maiores registradas via /criativa (MetricaMensal)
                _existing = {e.get("nome"): e.get("entregues", 0) for e in entry.get("entregas", [])}
                for _nome in list(counts.keys()):
                    _meta_val = metas_corretas.get(_nome, 4)
                    counts[_nome] = min(max(counts[_nome], _existing.get(_nome, 0)), _meta_val)

                for entrega in entry.get("entregas", []):
                    nome = entrega.get("nome")
                    if nome in counts and entrega.get("entregues") != counts[nome]:
                        entrega["entregues"] = counts[nome]
                        changed = True
                    meta_correta = metas_corretas.get(nome)
                    if meta_correta and entrega.get("meta") != meta_correta:
                        entrega["meta"] = meta_correta
                        changed = True

                links = {"link_relatorio": relatorio_link or relatorio_acc_link or relatorio_gt_link}
                if responsavel in ("gt", "cientista") or entry.get("link_kpi"):
                    links["link_kpi"] = kpis_link
                if responsavel in ("account", "cientista") or entry.get("link_forecast"):
                    links["link_forecast"] = forecasting_link
                for key, value in links.items():
                    if entry.get(key) != value:
                        entry[key] = value
                        changed = True

            if changed:
                record.entregas_operacao = lista
                flag_modified(record, "entregas_operacao")
                _recalcular_mrr_por_entregas(db, record)
                db.commit()
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[metrica sync periodo fast] ERRO: {e}")


def _sync_legacy_links_for_project(email, pipefy_id, mes, ano):
    """Concilia apenas links legados do projeto aberto, sem varrer o periodo."""
    try:
        with Session() as db:
            record = db.query(MetricaMensal).filter_by(
                email_investidor=email, mes=int(mes), ano=int(ano)
            ).first()
            if not record or not record.entregas_operacao:
                return

            entry = next(
                (e for e in record.entregas_operacao or [] if str(e.get("projeto_id")) == str(pipefy_id)),
                None,
            )
            if not entry:
                return

            row = db.execute(text(
                "SELECT id, entregas FROM plataforma_geral.operacao "
                "WHERE id_projeto = :id AND mes = :mes AND ano = :ano LIMIT 1"
            ), {"id": str(pipefy_id), "mes": int(mes), "ano": int(ano)}).mappings().first()
            if not row:
                return

            snap = row["entregas"] if isinstance(row["entregas"], dict) else (
                json.loads(row["entregas"]) if row["entregas"] else {}
            )
            responsavel = _infer_entregas_op_responsavel(
                db, email, int(pipefy_id), entry.get("responsavel", "")
            )
            if not _apply_legacy_links_to_snapshot_dict(snap, entry, responsavel):
                return

            db.execute(text(
                "UPDATE plataforma_geral.operacao "
                "SET entregas = CAST(:ent AS jsonb) WHERE id = :rid"
            ), {"ent": json.dumps(snap, ensure_ascii=False), "rid": row["id"]})
            db.commit()
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[snapshot legacy links] ERRO: {e}")


def _projeto_to_dict(projeto):
    """Converte um model de Projeto para dict compatível com os templates."""
    return {
        "id": projeto.pipefy_id,
        "pipefy_id": projeto.pipefy_id,
        "nome": projeto.nome,
        "documento": projeto.documento,
        "fee": projeto.fee,
        "moeda": projeto.moeda,
        "squad_atribuida": projeto.squad_atribuida,
        "produto_contratado": projeto.produto_contratado,
        "data_de_inicio": projeto.data_de_inicio.isoformat() if projeto.data_de_inicio else None,
        "cohort": projeto.cohort,
        "meta_account_id": projeto.meta_account_id,
        "google_account_id": projeto.google_account_id,
        "fase_do_pipefy": projeto.fase_do_pipefy,
        "step": projeto.step,
        "informacoes_gerais": projeto.informacoes_gerais,
        "orcamento_midia_meta": projeto.orcamento_midia_meta,
        "orcamento_midia_google": projeto.orcamento_midia_google,
        "data_fim": projeto.data_fim.isoformat() if projeto.data_fim else None,
        "url_webhook_gchat": projeto.url_webhook_gchat,
        "ekyte_workspace": projeto.ekyte_workspace,
        "extra": projeto.extra or {},
        "notas": projeto.notas or {},
        # Flag de contrato variável — lida do campo JSONB extra
        "contrato_variavel": bool((projeto.extra or {}).get("contrato_variavel", False)),
    }


def _agrupar_por_cliente(projetos_lista):
    """Agrupa projetos por nome do cliente, ordenados por id (replica lógica do hub_projetos original)."""
    projetos_ordenados = sorted(projetos_lista, key=lambda x: x.get("id", 0))
    clientes = defaultdict(list)
    for projeto in projetos_ordenados:
        cliente_nome = projeto.get("nome", "Cliente Desconhecido")
        clientes[cliente_nome].append(projeto)
    return dict(clientes)


def _buscar_projetos_db(model_class, email_investidor, squad_usuario, status=None):
    """Busca projetos no banco com a lógica do n8n: Gerência vê tudo, outros veem só o seu squad."""
    try:
        with Session() as db:
            u_posicao = session.get("posicao")
            
            # Se model_class for Projeto (unificado), adicionamos o filtro de status
            query = db.query(model_class)
            if model_class == Projeto and status:
                query = query.filter_by(status=status)
                
            if squad_usuario == "Gerência" or u_posicao in ["Gerência", "Sócio"]:
                projetos = query.all()
            elif u_posicao == "Coordenador":
                # Coordenador só vê dados da sua Squad; sem Squad, não vê nada
                if not squad_usuario:
                    return []
                projetos = query.filter_by(squad_atribuida=squad_usuario).all()
            else:
                projetos = query.filter_by(squad_atribuida=squad_usuario).all()
            return [_projeto_to_dict(p) for p in projetos]
    except SQLAlchemyError as e:
        print(f"Erro ao buscar projetos ({model_class.__tablename__}): {e}")
        return []

# ─── CONFIGURAÇÕES ────────────────────────────────────────────────────────────

UPLOAD_FOLDER = "static/images/profile_pictures"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/upload-profile-picture", methods=["POST"])
@check_session
def upload_profile_picture():

    if "foto" not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400

    arquivo = request.files["foto"]

    if arquivo.filename == "":
        return jsonify({"erro": "Nome de arquivo vazio"}), 400

    caminho = os.path.join(app.config["UPLOAD_FOLDER"], session["email"] + ".png")
    arquivo.save(caminho)

    with Session() as db:
        investidor = db.query(Investidor).filter_by(email=session["email"]).first()
        if investidor:
            investidor.profile_picture = session["email"] + ".png"
            db.commit()

    return jsonify({
        "mensagem": "Foto salva com sucesso",
        "arquivo": session["email"] + ".png",
        "caminho": caminho
    })

# ─── AUTENTICAÇÃO ────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        usuario = request.form["email"]
        senha = request.form["senha"]

        if usuario and senha:
            try:
                with Session() as db:
                    # 1. Busca usuário no banco (replica: SELECT * FROM investidores WHERE email = $email)
                    user = db.query(Investidor).filter_by(email=usuario).first()

                    if not user:
                        return render_template("login.html", error="E-mail e/ou Senha incorreto(s).")

                    if user.ativo is not True:
                        return render_template("login.html", error="Login inativo. Fale com a Gerência.")

                    if not check_password_hash(user.senha, senha):
                        return render_template("login.html", error="E-mail e/ou Senha incorreto(s).")

                    # 2. Gera token e faz UPSERT na tabela auth (replica comportamento do n8n)
                    token = os.urandom(10).hex()
                    auth_entry = db.get(Auth, user.email)
                    if auth_entry:
                        auth_entry.token = token
                    else:
                        max_id = db.query(Auth.id).order_by(Auth.id.desc()).first()
                        auth_entry = Auth(id=max_id[0] + 1, email=user.email, token=token)
                        db.add(auth_entry)
                    db.commit()

                    # 3. Popula sessão
                    session["nome"] = user.nome
                    session["email"] = user.email
                    session["token"] = token
                    session["funcao"] = user.funcao
                    session["posicao"] = user.posicao
                    session["senioridade"] = user.senioridade
                    session["squad"] = user.squad
                    session["nivel_acesso"] = user.nivel_acesso
                    session["pode_editar_kanban"] = user.pode_editar_kanban
                    session["profile_picture"] = user.profile_picture

                    if request.form.get("remember"):
                        session.permanent = True

                    print(session)

                    return redirect(url_for("home"))

            except SQLAlchemyError as e:
                print(f"Erro de banco no login: {e}")
                return render_template("login.html", error="Erro ao conectar ao banco de dados.")

    return render_template("login.html")


@app.route("/login/google")
def login_google():
    google = OAuth2Session(GOOGLE_CLIENT_ID, scope=GOOGLE_SCOPE, redirect_uri=REDIRECT_URI)
    authorization_url, state = google.authorization_url(
        AUTHORIZATION_BASE_URL,
        access_type="offline",
        prompt="select_account",
    )
    session["oauth_state"] = state
    return redirect(authorization_url)


@app.route("/login/callback")
def login_callback():
    state = session.get("oauth_state")
    if not state:
        return render_template("login.html", error="Sessão expirada. Tente fazer login novamente.")

    google = OAuth2Session(GOOGLE_CLIENT_ID, state=state, redirect_uri=REDIRECT_URI)
    try:
        token = google.fetch_token(
            TOKEN_URL,
            client_secret=GOOGLE_CLIENT_SECRET,
            authorization_response=request.url,
        )
    except Exception as e:
        print(f"[Google OAuth] Erro ao obter token: {e}")
        import traceback; traceback.print_exc()
        return render_template("login.html", error="Falha na autenticação com Google.")

    resp = google.get("https://www.googleapis.com/oauth2/v1/userinfo")
    user_info = resp.json()
    email = user_info.get("email")
    name = user_info.get("name")

    if not email:
        return render_template("login.html", error="Não foi possível obter o e-mail do Google.")

    with Session() as db:
        user = db.query(Investidor).filter_by(email=email).first()
        if not user:
            return render_template(
                "login.html",
                error=f"E-mail {email} não encontrado no sistema. Contate a Gerência.",
            )
        if user.ativo is not True:
            return render_template("login.html", error="Login inativo. Fale com a Gerência.")

        token_auth = os.urandom(10).hex()
        auth_entry = db.get(Auth, user.email)
        if auth_entry:
            auth_entry.token = token_auth
        else:
            max_id = db.query(Auth.id).order_by(Auth.id.desc()).first()
            auth_entry = Auth(id=(max_id[0] + 1) if max_id else 1, email=user.email, token=token_auth)
            db.add(auth_entry)
        db.commit()

    session["nome"] = user.nome
    session["email"] = user.email
    session["token"] = token_auth
    session["funcao"] = user.funcao
    session["posicao"] = user.posicao
    session["senioridade"] = user.senioridade
    session["squad"] = user.squad
    session["nivel_acesso"] = user.nivel_acesso
    session["pode_editar_kanban"] = user.pode_editar_kanban
    session["profile_picture"] = user.profile_picture
    session.permanent = True

    return redirect(url_for("home"))


@app.route("/dev-login")
def dev_login():
    with Session() as db:
        user = db.query(Investidor).filter_by(email="ronaldo.teixeira@v4company.com").first()
        if user:
            session.clear()
            session["nome"] = user.nome
            session["email"] = user.email
            session["token"] = "dev-token"
            session["funcao"] = user.funcao
            session["posicao"] = user.posicao
            session["senioridade"] = user.senioridade
            session["squad"] = user.squad
            session["nivel_acesso"] = user.nivel_acesso
            session["pode_editar_kanban"] = True
            session["profile_picture"] = user.profile_picture
            return redirect(url_for("view_kanban"))
        return "Dev user not found", 404


# Rota para alterar senha sem render_template
@app.route("/alterar-senha", methods=["POST"])
@check_session
def alterar_senha():
    try:
        with Session() as db:
            user = db.query(Investidor).filter_by(email=session["email"]).first()
            if not user:
                return "Usuário não encontrado", 404

            senha_atual = request.form["senha_atual"]
            nova_senha = request.form["nova_senha"]
            confirmar_senha = request.form["confirmar_senha"]

            if not senha_atual or not nova_senha or not confirmar_senha:
                return "Preencha todos os campos", 400

            if nova_senha != confirmar_senha:
                return "As senhas não coincidem", 400

            if not check_password_hash(user.senha, senha_atual):
                return "Senha atual incorreta", 400

            user.senha = generate_password_hash(nova_senha)
            db.commit()

            return "Senha alterada com sucesso", 200

    except SQLAlchemyError as e:
        print(f"Erro ao alterar senha: {e}")
        return "Erro ao conectar ao banco de dados", 500

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ─── PÁGINAS ─────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
@check_session
def home():
    try:
        from services.currency import CurrencyService
        with Session() as db:
            clients_count = db.query(Projeto).filter_by(status='Ativo').count()
            investors_count = db.query(Investidor).count()
            squads_count = db.query(Projeto.squad_atribuida).filter(
                Projeto.status == 'Ativo',
                Projeto.squad_atribuida != None, 
                Projeto.squad_atribuida != ""
            ).distinct().count()

            # MRR Global: Apenas Ativos (recorrentes)
            projetos_ativos = db.query(Projeto).filter_by(status='Ativo').all()
            projetos = projetos_ativos
            
            mrr_total = 0
            usd_rate = None
            for p in projetos:
                fee = float(p.fee or 0)
                m_code = str(p.moeda).strip().upper() if p.moeda else "BRL"
                if m_code == 'USD':
                    if usd_rate is None:
                        usd_rate = float(CurrencyService.get_usd_to_brl_rate())
                    mrr_total += fee * usd_rate
                else:
                    mrr_total += fee


            operational_data = {
                "mrr": mrr_total,
                "clients": clients_count,
                "investors": investors_count,
                "squads": squads_count
            }
    except Exception as e:
        import traceback
        with open("error_log_home1.txt", "w") as f:
            f.write(traceback.format_exc())
        print(f"Erro ao carregar dados operacionais: {e}")
        operational_data = {
            "mrr": 0,
            "clients": 0,
            "investors": 0,
            "squads": 0
        }

    # ── Métricas de remuneração do usuário logado ──────────────────────────────
    my_remuneracao = None
    try:
        user_email = session.get("email")
        with Session() as db:
            # Busca métricas do usuário logado (mais recente primeiro)
            metricas_raw = db.query(MetricaMensal, Investidor).join(
                Investidor, MetricaMensal.email_investidor == Investidor.email
            ).filter(
                MetricaMensal.email_investidor == user_email
            ).order_by(
                MetricaMensal.ano.desc(),
                MetricaMensal.mes.desc()
            ).all()

            if metricas_raw:
                hoje = dt.now()
                mes_atual = hoje.month
                ano_atual = hoje.year

                from sqlalchemy import extract, or_, and_
                # Projetos vinculados (ativos + churned no mês corrente)
                vinculos = db.query(InvestidorProjeto).filter(
                    InvestidorProjeto.email_investidor == user_email,
                    or_(
                        InvestidorProjeto.active == True,
                        and_(
                            InvestidorProjeto.active == False,
                            extract('month', InvestidorProjeto.inactivated_at) == mes_atual,
                            extract('year', InvestidorProjeto.inactivated_at) == ano_atual
                        )
                    )
                ).all()

                # Buscar metadata dos projetos (moeda) para conversão
                projeto_metadata = {}
                # Buscar metadata dos projetos (moeda) para conversão na tabela unificada
                rows = db.query(Projeto.pipefy_id, Projeto.moeda).all()
                for r in rows:
                    if r.pipefy_id:
                        projeto_metadata[str(r.pipefy_id)] = str(r.moeda).strip().upper() if r.moeda else "BRL"

                usd_rate = None
                projetos_vinculados = []
                for v in vinculos:
                    pid_str = str(v.pipefy_id_projeto)
                    moeda = projeto_metadata.get(pid_str, "BRL")
                    fee = float(v.fee_projeto or 0)
                    
                    if moeda == "USD":
                        if usd_rate is None:
                            usd_rate = float(CurrencyService.get_usd_to_brl_rate())
                        # fee = fee * usd_rate # Opcional: converter aqui ou passar a moeda
                        # Decidimos passar o fee original e a moeda para que o JS saiba como exibir
                        pass

                    projetos_vinculados.append({
                        "id": v.pipefy_id_projeto,
                        "nome": v.nome_projeto,
                        "fee": fee,
                        "moeda": moeda,
                        "active": v.active
                    })

                clients_count_user = db.query(InvestidorProjeto).filter_by(
                    email_investidor=user_email, active=True
                ).count()

                # Pega os dados fixos da primeira (mais recente) métrica
                primeira_metrica, investidor = metricas_raw[0]

                rows = []
                for metrica, _ in metricas_raw:
                    rows.append({
                        "month_year": f"{metrica.mes:02d}/{metrica.ano}",
                        "mrr": float(metrica.fixo_mrr_entrega or 0),
                        "mrrTotal": float(metrica.fixo_mrr_projeto_total or 0),
                        "churn": float(metrica.calc_churn_real_percentual or 0),
                        "churn_rs": float(metrica.fixo_churn_atual or 0),
                        "variable_brl": float(metrica.calc_variavel_total or 0),
                        "total_brl": max(float(metrica.calc_remuneracao_total or 0), float(metrica.fixo_remuneracao_minima or 0)),
                        "rem_min": float(metrica.fixo_remuneracao_minima or 0),
                        "rem_max": float(metrica.fixo_remuneracao_maxima or 0),
                        "yellow_streak": metrica.yellow_streak or 0,
                        "green_streak": metrica.green_streak or 0,
                        "motivo_flag": metrica.motivo_flag or "",
                        "role": investidor.funcao or investidor.posicao,
                        "senioridade": metrica.senioridade or investidor.senioridade or "",
                        "nivel": metrica.level or investidor.nivel or "",
                        "fixed_fee": float(primeira_metrica.fixo_remuneracao_fixa or 0),
                    })

                # Inverte para que [-1] seja o mais recente (igual ao hub_remuneracao)
                rows.reverse()

                last_row = rows[-1] if rows else {}
                rem_atual = float(primeira_metrica.calc_remuneracao_total or 0)
                rem_min = float(primeira_metrica.fixo_remuneracao_minima or 0)
                rem_max = float(primeira_metrica.fixo_remuneracao_maxima or 0)

                # Trava remuneração entre mínimo e máximo do colaborador
                if rem_min and rem_atual < rem_min:
                    rem_atual = rem_min
                if rem_max and rem_atual > rem_max:
                    rem_atual = rem_max

                my_remuneracao = {
                    "name": investidor.nome,
                    "role": investidor.funcao or investidor.posicao,
                    "squad": investidor.squad,
                    "profile_picture": investidor.profile_picture,
                    "fixed_fee": float(primeira_metrica.fixo_remuneracao_fixa or 0),
                    "mrr": float(primeira_metrica.fixo_mrr_atual or 0),
                    "mrrTotal": float(primeira_metrica.fixo_mrr_projeto_total or 0),
                    "mrrEsperado": float(primeira_metrica.fixo_mrr_esperado or 0),
                    "mrrTeto": float(primeira_metrica.fixo_mrr_teto or 0),
                    "rem_min": rem_min,
                    "rem_max": rem_max,
                    "rem_atual": round(rem_atual, 2),
                    "churn_rs": last_row.get("churn_rs", 0),
                    "clients_count": clients_count_user,
                    "projetos_total": len(projetos_vinculados),
                    "projetos_vinculados": projetos_vinculados,
                    "rows": rows,
                }
    except Exception as e:
        import traceback
        with open("error_log_home2.txt", "w") as f:
            f.write(traceback.format_exc())
        print(f"Erro ao carregar remuneração do usuário: {e}")
        my_remuneracao = None
    # ── Fim métricas de remuneração ────────────────────────────────────────────

    return render_template("index.html", operational_data=operational_data, my_remuneracao=my_remuneracao)


@app.template_filter('format_date')
def format_date(date_str):
    if not date_str:
        return 'N/A'
    date_part = date_str.split('T')[0]
    year, month, day = date_part.split('-')
    return f'{day}/{month}/{year}'


@app.route("/hub-projetos", methods=["GET"])
@check_session
def hub_projetos():
    squad = session.get("squad", "")
    email = session.get("email", "")

    # Busca squads disponíveis para o usuário (projetos ativos onde ele está no squad)
    try:
        with Session() as db:
            u_posicao = session.get("posicao")
            if squad == "Gerência" or u_posicao in ["Gerência", "Sócio"]:
                projetos_squad = db.query(Projeto).filter_by(status='Ativo').all()
            elif u_posicao == "Coordenador":
                # Coordenador só vê sua própria squad; se não tiver squad, não vê nada
                if not squad:
                    projetos_squad = []
                else:
                    projetos_squad = db.query(Projeto).filter_by(status='Ativo', squad_atribuida=squad).all()
            else:
                projetos_squad = db.query(Projeto).filter_by(status='Ativo', squad_atribuida=squad).all()
            squads = list(set(p.squad_atribuida for p in projetos_squad if p.squad_atribuida))
    except SQLAlchemyError as e:
        print(f"Erro ao buscar squads: {e}")
        squads = []

    ativos_data = _buscar_projetos_db(Projeto, email, squad, status='Ativo')
    ativos = _agrupar_por_cliente(ativos_data)

    onetime_data = _buscar_projetos_db(Projeto, email, squad, status='Onetime')
    onetime = _agrupar_por_cliente(onetime_data)

    inativos_data = _buscar_projetos_db(Projeto, email, squad, status='Inativo')
    inativos = _agrupar_por_cliente(inativos_data)

    return render_template(
        "hub-projetos.html",
        clientes_ativos=ativos,
        clientes_onetime=onetime,
        clientes_inativos=inativos,
        squads=squads
    )


@app.route("/hub-remuneracao")
@check_session
@check_access(["Gerência", "Sócio", "Coordenador"])
def hub_remuneracao():
    try:
        with Session() as db:
            # 1. Busca contagem de clientes por investidor
            client_counts = db.query(
                InvestidorProjeto.email_investidor, 
                text("count(pipefy_id_projeto) as total")
            ).filter(InvestidorProjeto.active == True).group_by(InvestidorProjeto.email_investidor).all()
            clients_map = {email: count for email, count in client_counts}

            # 2. Busca projetos vinculados por investidor para mapeamento
            # Considera projetos ativos ou inativados nos últimos 2 meses para rastreabilidade
            hoje = dt.now()
            from datetime import timedelta
            primeiro_dia_mes_atual = dt(hoje.year, hoje.month, 1)
            mes_passado = primeiro_dia_mes_atual - timedelta(days=1)

            from sqlalchemy import extract, or_, and_
            all_vinculos = db.query(InvestidorProjeto).filter(
                or_(
                    InvestidorProjeto.active == True,
                    and_(
                        InvestidorProjeto.active == False,
                        InvestidorProjeto.inactivated_at >= dt(mes_passado.year, mes_passado.month, 1)
                    )
                )
            ).all()

            # Buscar de todas as tabelas para garantir cobertura de onetimes e inativos
            # Buscar da tabela unificada para garantir cobertura de onetimes e inativos
            projeto_metadata = {}
            rows = db.query(Projeto.pipefy_id, Projeto.moeda).all()
            for r in rows:
                if r.pipefy_id:
                    projeto_metadata[str(r.pipefy_id)] = str(r.moeda).strip().upper() if r.moeda else "BRL"

            projetos_map = {}
            for v in all_vinculos:
                if v.email_investidor not in projetos_map:
                    projetos_map[v.email_investidor] = []
                # Inclui ID, Nome, Fee e Moeda para exibição detalhada
                pid_str = str(v.pipefy_id_projeto)
                projetos_map[v.email_investidor].append({
                    "id": v.pipefy_id_projeto,
                    "nome": v.nome_projeto,
                    "fee": float(v.fee_projeto or 0),
                    "moeda": projeto_metadata.get(pid_str, "BRL"),
                    "active": v.active
                })


            # 2. Busca métricas mais recentes agrupadas por investidor
            u_posicao = session.get("posicao")
            u_squad = session.get("squad")

            query_metricas = db.query(MetricaMensal, Investidor).join(
                Investidor, MetricaMensal.email_investidor == Investidor.email
            )

            # Se for Coordenador, filtra apenas pela própria squad
            if u_posicao == "Coordenador":
                if not u_squad:
                    metricas_raw = []
                else:
                    metricas_raw = query_metricas.filter(Investidor.squad == u_squad).order_by(
                        MetricaMensal.email_investidor,
                        MetricaMensal.ano.desc(),
                        MetricaMensal.mes.desc()
                    ).all()
            else:
                metricas_raw = query_metricas.order_by(
                    MetricaMensal.email_investidor,
                    MetricaMensal.ano.desc(),
                    MetricaMensal.mes.desc()
                ).all()

        # Agrupa histórico por investidor
        investidores_dict = {}
        for metrica, investidor in metricas_raw:
            email = metrica.email_investidor

            # Filtra posições de gestão/coordenação da listagem
            if investidor.posicao and investidor.posicao in ["Gerência", "Sócio", "Coordenador"]:
                continue

            if email not in investidores_dict:
                investidores_dict[email] = {
                    "id": f"inv_{email.replace('@', '_').replace('.', '_')}",
                    "name": investidor.nome,
                    "email": investidor.email,
                    "profile_picture": investidor.profile_picture,
                    "role": investidor.funcao or investidor.posicao,
                    "squad": investidor.squad,
                    "senioridade": metrica.senioridade or investidor.senioridade,
                    "nivel": metrica.level or investidor.nivel,
                    "step": metrica.level,
                    "clients_count": clients_map.get(email, 0),
                    "fixed_fee": float(metrica.fixo_remuneracao_fixa or 0),
                    "projetos_vinculados": json.dumps(projetos_map.get(email, [])),
                    "mrr": float(metrica.fixo_mrr_entrega or 0),
                    "mrrTotal": float(metrica.fixo_mrr_projeto_total or 0),
                    "mrrEsperado": float(metrica.fixo_mrr_esperado or 0),
                    "mrrTeto": float(metrica.fixo_mrr_teto or 0),
                    "roi": float(metrica.calc_delta_csp or 0),
                    "rem_min": float(metrica.fixo_remuneracao_minima or 0),
                    "rem_max": float(metrica.fixo_remuneracao_maxima or 0),
                    "flag": metrica.flag,
                    "ativo": metrica.ativo,
                    "rows": [],
                }

            investidores_dict[email]["rows"].append({
                "month_year": f"{metrica.mes:02d}/{metrica.ano}",
                "mrr": float(metrica.fixo_mrr_entrega or 0),
                "mrrTotal": float(metrica.fixo_mrr_projeto_total or 0),
                "churn": float(metrica.calc_churn_real_percentual or 0),
                "churn_rs": float(metrica.fixo_churn_atual or 0),
                "variable_brl": float(metrica.calc_variavel_total or 0),
                "total_brl": max(float(metrica.calc_remuneracao_total or 0), float(metrica.fixo_remuneracao_minima or 0)),
                "rem_min": float(metrica.fixo_remuneracao_minima or 0),
                "rem_max": float(metrica.fixo_remuneracao_maxima or 0),
                "yellow_streak": metrica.yellow_streak or 0,
                "green_streak": metrica.green_streak or 0,
                "motivo_flag": metrica.motivo_flag or "",
            })

        # Inverte as rows para que fiquem em ordem cronológica na tabela (antigo -> novo) if needed
        # ou mantém decrescente dependendo do que o template espera. O template faz inv.rows[-1] para o mais recente.
        # Como ordenamos desc no SQL, o primeiro [0] é o mais novo, e o último [-1] é o mais antigo.
        # Ajuste: se o template usa [-1] para o "status atual", devemos inverter a lista para que o mais recente seja o último.
        for email in investidores_dict:
            investidores_dict[email]["rows"].reverse()

        mock_investors = list(investidores_dict.values())
        squads = sorted(list(set(inv["squad"] for inv in mock_investors if inv["squad"])))
        roles = sorted(list(set(inv["role"] for inv in mock_investors if inv["role"])))

    except SQLAlchemyError as e:
        print(f"Erro ao buscar remuneração: {e}")
        mock_investors = []
        squads = []
        roles = []

    return render_template(
        "hub-remuneracao.html",
        investors=mock_investors,
        squads=squads,
        roles=roles
    )


# ─── FOTO DE USUÁRIO (LEITURA P/ USUÁRIOS LOGADOS) ───────────────────────────

@app.route("/api/usuarios/<email>/foto", methods=["GET"])
@check_session
def api_get_foto_usuario(email):
    """Retorna apenas a URL da foto de perfil de um usuário pelo email.
    Endpoint isolado, somente leitura — não modifica dados nem regras existentes."""
    try:
        with Session() as db:
            user = db.query(Investidor).filter(Investidor.email == email).first()
            if not user or not user.profile_picture:
                return jsonify({"foto": None, "nome": email.split("@")[0] if email and "@" in email else email})
            return jsonify({
                "foto": f"/static/images/profile_pictures/{user.profile_picture}",
                "nome": user.nome or email.split("@")[0]
            })
    except Exception as e:
        return jsonify({"foto": None, "error": str(e)}), 500


# ─── GERENCIAMENTO DE USUÁRIOS (ADMIN) ───────────────────────────────────────

@app.route("/gerenciar-usuarios")
@check_session
def gerenciar_usuarios():
    # Apenas Admin acessa essa tela
    if session.get("nivel_acesso") != "Admin":
        return render_template("index.html", error="Acesso restrito a administradores.")
    
    try:
        with Session() as db:
            # Buscar opções para os selects do modal
            from models import RemuneracaoCargo
            cargos = db.query(RemuneracaoCargo.fixo_cargo).distinct().all()
            senioridades = db.query(RemuneracaoCargo.fixo_senioridade).distinct().all()
            niveis = db.query(RemuneracaoCargo.fixo_level).distinct().all()
            
            # Posições e Squads fixas ou do banco
            posicoes = ["Operação", "Gerência", "Meio", "Sócio", "Coordenador"]
            squads_db = db.query(Investidor.squad).filter(Investidor.squad != None).distinct().all()
            squads = sorted(list(set([s[0] for s in squads_db if s[0]] + ["Gerência", "Strike Force", "Shark", "Tigers"])))

            return render_template(
                "gerenciar-usuarios.html",
                options={
                    "cargos": [c[0] for c in cargos],
                    "senioridades": [s[0] for s in senioridades],
                    "niveis": [n[0] for n in niveis],
                    "posicoes": posicoes,
                    "squads": squads
                }
            )
    except Exception as e:
        print(f"Erro ao carregar gerenciar usuários: {e}")
        return redirect(url_for("home"))


@app.route("/api/admin/usuarios", methods=["GET"])
@check_session
def api_get_usuarios():
    if session.get("nivel_acesso") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        with Session() as db:
            usuarios = db.query(Investidor).order_by(Investidor.nome).all()
            return jsonify([{
                "id": u.id,
                "nome": u.nome,
                "email": u.email,
                "funcao": u.funcao,
                "senioridade": u.senioridade,
                "nivel": u.nivel,
                "squad": u.squad,
                "posicao": u.posicao,
                "nivel_acesso": u.nivel_acesso,
                "ativo": u.ativo,
                "pode_editar_kanban": u.pode_editar_kanban,
                "profile_picture": u.profile_picture or ""
            } for u in usuarios])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/usuarios", methods=["POST"])
@check_session
def api_create_usuario():
    if session.get("nivel_acesso") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    try:
        with Session() as db:
            # Verifica se já existe
            exists = db.query(Investidor).filter_by(email=data["email"]).first()
            if exists:
                return jsonify({"error": "Usuário com este e-mail já existe."}), 400

            # Gerar ID sequencial se não fornecido
            if not data.get("id"):
                max_id = db.query(Investidor.id).order_by(Investidor.id.desc()).first()
                new_id = (max_id[0] + 1) if max_id else 1
            else:
                new_id = data["id"]

            novo_user = Investidor(
                id=new_id,
                nome=data["nome"],
                email=data["email"],
                funcao=data.get("funcao"),
                senioridade=data.get("senioridade"),
                nivel=data.get("nivel"),
                squad=data.get("squad"),
                posicao=data.get("posicao"),
                nivel_acesso=data.get("nivel_acesso", "Usuário"),
                ativo=data.get("ativo", True),
                pode_editar_kanban=data.get("pode_editar_kanban", False),
                senha=generate_password_hash(data.get("senha", "v4company")) # Senha padrão se não enviada
            )
            db.add(novo_user)
            db.commit()
            return jsonify({"status": "success", "message": "Usuário criado com sucesso!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/usuarios/<email>", methods=["PUT"])
@check_session
def api_update_usuario(email):
    if session.get("nivel_acesso") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    try:
        with Session() as db:
            user = db.query(Investidor).filter_by(email=email).first()
            if not user:
                return jsonify({"error": "Usuário não encontrado."}), 404

            user.nome = data.get("nome", user.nome)
            user.funcao = data.get("funcao", user.funcao)
            user.senioridade = data.get("senioridade", user.senioridade)
            user.nivel = data.get("nivel", user.nivel)
            user.squad = data.get("squad", user.squad)
            user.posicao = data.get("posicao", user.posicao)
            user.nivel_acesso = data.get("nivel_acesso", user.nivel_acesso)
            user.ativo = data.get("ativo", user.ativo)
            user.pode_editar_kanban = data.get("pode_editar_kanban", user.pode_editar_kanban)
            
            # Se vier senha nova, atualiza
            if data.get("senha"):
                user.senha = generate_password_hash(data["senha"])

            db.commit()
            return jsonify({"status": "success", "message": "Usuário atualizado com sucesso!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/usuarios/reset-password", methods=["POST"])
@check_session
def api_reset_password():
    if session.get("nivel_acesso") != "Admin":
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    email = data.get("email")
    nova_senha = data.get("nova_senha", "v4company")
    
    try:
        with Session() as db:
            user = db.query(Investidor).filter_by(email=email).first()
            if not user:
                return jsonify({"error": "Usuário não encontrado."}), 404
            
            user.senha = generate_password_hash(nova_senha)
            db.commit()
            return jsonify({"status": "success", "message": f"Senha de {email} redefinida com sucesso!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── OUTRAS PÁGINAS ──────────────────────────────────────────────────────────

@app.route("/painel-atribuicao", methods=["GET"])
@check_session
def painel_atribuicao():
    return render_template("painel-atribuicao.html")


@app.route("/painel-ranking", methods=["GET"])
@check_session
def painel_ranking():
    return render_template("painel-ranking.html")


@app.route("/vendas", methods=["GET"])
@check_session
def vendas():
    return render_template("vendas.html")


@app.route("/operacao", methods=["GET"])
@check_session
@check_access(["Account", "Gestor de Tráfego"])
def operacao():
    email = session.get("email")
    squad = session.get("squad")
    posicao = session.get("posicao")
    
    try:
        with Session() as db:
            meus_projetos = OperacaoService.get_projetos_operacao(db, email, squad, posicao)
            if meus_projetos:
                project_ids = [p["pipefy_id"] for p in meus_projetos if p.get("pipefy_id")]
                if project_ids:
                    inativos_ids = {
                        row.pipefy_id
                        for row in db.query(Projeto.pipefy_id)
                        .filter(Projeto.pipefy_id.in_(project_ids), Projeto.status == 'Inativo')
                        .all()
                    }
                    meus_projetos = [p for p in meus_projetos if p.get("pipefy_id") not in inativos_ids]
            
    except SQLAlchemyError as e:
        print(f"Erro ao carregar operação: {e}")
        meus_projetos = []

    return render_template("operacao.html", projetos=meus_projetos)


@app.route("/criativa", methods=["GET"])
@check_session
@check_access(["Designer", "WebDesigner", "Account", "Gestor de Tráfego", "Coordenador"])
def criativa():
    mes = request.args.get("mes", type=int) or dt.now().month
    ano = request.args.get("ano", type=int) or dt.now().year

    try:
        from services.currency import CurrencyService
        usd_rate = float(CurrencyService.get_usd_to_brl_rate())
    except Exception:
        usd_rate = 5.7  # fallback

    try:
        with Session() as db:
            query = db.query(Investidor).filter(
                Investidor.funcao.ilike("Designer") |
                Investidor.funcao.ilike("WebDesigner") |
                Investidor.funcao.ilike("Account") |
                Investidor.funcao.ilike("Gestor de Tráfego"),
                Investidor.ativo == True
            )

            # Regras de visualização por Cargo/Squad
            u_email = session.get("email")
            u_posicao = session.get("posicao", "")
            u_squad = session.get("squad", "")
            u_acesso = session.get("nivel_acesso", "")

            if u_acesso == "Admin" or u_posicao in ["Gerência", "Sócio"]:
                # Vê tudo sem filtros adicionais
                pass
            elif u_posicao == "Coordenador":
                # Vê apenas membros da própria squad
                query = query.filter(Investidor.squad == u_squad)
            else:
                # Vê apenas a si mesmo
                query = query.filter(Investidor.email == u_email)

            designers = query.order_by(Investidor.squad, Investidor.nome).all()

            # Clientes que estavam ativos DURANTE o mês selecionado
            from sqlalchemy import or_, and_
            _start_mes = dt(ano, mes, 1, 0, 0, 0)
            _end_mes_exc = dt(ano + 1, 1, 1) if mes == 12 else dt(ano, mes + 1, 1)
            projetos_rows = db.query(InvestidorProjeto).filter(
                # Foi adicionado antes ou durante o mês selecionado
                or_(
                    InvestidorProjeto.created_at == None,
                    InvestidorProjeto.created_at < _end_mes_exc
                ),
                # Não deu churn antes do início do mês selecionado
                or_(
                    InvestidorProjeto.active == True,
                    and_(
                        InvestidorProjeto.active == False,
                        InvestidorProjeto.inactivated_at >= _start_mes
                    )
                )
            ).all()

            # Fee e moeda por projeto (pipefy_id → {fee, moeda})
            projeto_fees = {}
            
            # Buscar de todas as tabelas para garantir cobertura de onetimes e inativos
            all_fee_rows = db.query(Projeto.pipefy_id, Projeto.fee, Projeto.moeda).all()
            
            for row in all_fee_rows:
                if row.pipefy_id:
                    try:
                        projeto_fees[str(row.pipefy_id)] = {
                            "fee": float(row.fee or 0),
                            "moeda": str(row.moeda).strip().upper() if row.moeda else "BRL",
                        }
                    except (ValueError, TypeError):
                        projeto_fees[str(row.pipefy_id)] = {"fee": 0, "moeda": "BRL"}

            clientes_por_email = {}  # email → [{nome, projeto_id, fee, moeda}]
            for p in projetos_rows:
                email = p.email_investidor
                nome = (p.nome_projeto or "").strip()
                projeto_id = p.pipefy_id_projeto
                if not nome or not projeto_id:
                    continue
                if email not in clientes_por_email:
                    clientes_por_email[email] = []
                info = projeto_fees.get(str(projeto_id), {"fee": 0, "moeda": "BRL"})
                if not any(c["projeto_id"] == projeto_id for c in clientes_por_email[email]):
                    clientes_por_email[email].append({
                        "nome": nome,
                        "projeto_id": projeto_id,
                        "fee": info["fee"],
                        "moeda": info["moeda"],
                        "cientista": bool(p.cientista),
                        "churned": not p.active,
                        "data_churn": p.inactivated_at.strftime("%d/%m/%Y") if p.inactivated_at else None
                    })

            # Carrega entregas_criativos de investidores_metricas_mensais_novo
            emails = [d.email for d in designers if d.email]
            entregas_map = {}  # email → lista de objetos de entrega
            if emails:
                entregas_rows = db.query(MetricaMensal).filter(
                    MetricaMensal.email_investidor.in_(emails),
                    MetricaMensal.mes == mes,
                    MetricaMensal.ano == ano,
                ).all()
                for ec in entregas_rows:
                    entregas_map[ec.email_investidor] = ec.entregas_criativos or []

            # Carrega dados de remuneração para todos os membros da equipe
            op_emails = [d.email for d in designers if d.email]
            remu_map = {}
            if op_emails:
                remu_rows_all = db.query(MetricaMensal).filter(
                    MetricaMensal.email_investidor.in_(op_emails),
                ).order_by(
                    MetricaMensal.email_investidor,
                    MetricaMensal.ano.desc(),
                    MetricaMensal.mes.desc()
                ).all()

                remu_by_email = {}
                for m in remu_rows_all:
                    e = m.email_investidor
                    if e not in remu_by_email:
                        remu_by_email[e] = {"latest": m, "rows": []}
                    remu_by_email[e]["rows"].append({
                        "month_year": f"{m.mes:02d}/{m.ano}",
                        "mes": m.mes,
                        "ano": m.ano,
                        "mrr": float(m.fixo_mrr_atual or 0),
                        "mrr_bruto_entregue": float(m.fixo_mrr_entrega or 0),
                        "mrr_total": float(m.fixo_mrr_projeto_total or 0),
                        "mrr_esperado": float(m.fixo_mrr_esperado or 0),
                        "mrr_teto": float(m.fixo_mrr_teto or 0),
                        "churn": float(m.calc_churn_real_percentual or 0),
                        "churn_rs": float(m.fixo_churn_atual or 0),
                        "variable_brl": float(m.calc_variavel_total or 0),
                        "total_brl": max(float(m.calc_remuneracao_total or 0), float(m.fixo_remuneracao_minima or 0)),
                        "rem_min": float(m.fixo_remuneracao_minima or 0),
                        "rem_max": float(m.fixo_remuneracao_maxima or 0),
                        "yellow_streak": m.yellow_streak or 0,
                        "green_streak": m.green_streak or 0,
                        "motivo_flag": m.motivo_flag or "",
                        "cargo": m.cargo or "",
                        "senioridade": m.senioridade or "",
                        "nivel": m.level or "",
                        "fixo": float(m.fixo_remuneracao_fixa or 0),
                    })

                for e, data in remu_by_email.items():
                    data["rows"].reverse()  # ordem cronológica, mais recente por último
                    m = data["latest"]
                    rows = data["rows"]
                    rem_atual = 0
                    if rows:
                        last = rows[-1]
                        rem_atual = max(min(last["total_brl"], last["rem_max"]), last["rem_min"])
                    remu_map[e] = {
                        "fixed_fee": float(m.fixo_remuneracao_fixa or 0),
                        "mrr": float(m.fixo_mrr_atual or 0),
                        "mrr_total": float(m.fixo_mrr_projeto_total or 0),
                        "mrr_esperado": float(m.fixo_mrr_esperado or 0),
                        "mrr_teto": float(m.fixo_mrr_teto or 0),
                        "rem_min": float(m.fixo_remuneracao_minima or 0),
                        "rem_max": float(m.fixo_remuneracao_maxima or 0),
                        "rem_atual": rem_atual,
                        "churn_rs": float(m.fixo_churn_atual or 0),
                        "flag": m.flag or "",
                        "yellow_streak": m.yellow_streak or 0,
                        "green_streak": m.green_streak or 0,
                        "rows": rows,
                    }

            squads = {}
            for d in designers:
                squad = d.squad or "Sem Squad"
                clientes = sorted(
                    clientes_por_email.get(d.email, []),
                    key=lambda x: x["nome"]
                )
                entregas_designer = entregas_map.get(d.email, [])

                clientes_json = []
                for c in clientes:
                    entry = get_entregas_by_projeto(entregas_designer, c["projeto_id"])
                    clientes_json.append({
                        "nome": c["nome"],
                        "projeto_id": c["projeto_id"],
                        "fee": c.get("fee", 0),
                        "moeda": c.get("moeda", "BRL"),
                        "cientista": c.get("cientista", False),
                        "churned": c.get("churned", False),
                        "data_churn": c.get("data_churn", None),
                        "link_criativos": entry.get("link_criativos", "") if entry else "",
                        "criativos_c": entry["criativos"]["contratados"] if entry else 0,
                        "criativos_e": entry["criativos"]["entregues"] if entry else 0,
                        "videos_c": entry["videos"]["contratados"] if entry else 0,
                        "videos_e": entry["videos"]["entregues"] if entry else 0,
                        "lps_c": entry["lp"]["contratados"] if entry else 0,
                        "lps_e": entry["lp"]["entregues"] if entry else 0,
                    })

                if squad not in squads:
                    squads[squad] = []
                squads[squad].append({
                    "nome": d.nome,
                    "funcao": d.funcao,
                    "senioridade": d.senioridade or "",
                    "profile_picture": d.profile_picture or "",
                    "email": d.email or "",
                    "squad": squad,
                    "clientes": [c["nome"] for c in clientes],
                    "clientes_json": clientes_json,
                    "remu_json": remu_map.get(d.email, {}),
                })
    except Exception as e:
        print(f"Erro ao carregar designers: {e}")
        squads = {}

    return render_template("criativa.html", squads=squads, mes=mes, ano=ano, usd_rate=usd_rate, now_mes=dt.now().month, now_ano=dt.now().year)


# ─── APIs CRIATIVA ───────────────────────────────────────────────────────────

@app.route("/api/criativa/entregas/<email>/<int:mes>/<int:ano>", methods=["GET"])
@check_session
@check_access(["Designer", "WebDesigner", "Account", "Gestor de Tráfego"])
def get_entregas_criativa(email, mes, ano):
    """Retorna entregas_criativos de investidores_metricas_mensais_novo para o designer/mês/ano."""
    try:
        with Session() as db:
            record = db.query(MetricaMensal).filter_by(
                email_investidor=email, mes=mes, ano=ano
            ).first()
            return jsonify(record.entregas_criativos if record else [])
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/criativa/entregas/contratados", methods=["PUT"])
@check_session
def update_criativa_contratados():
    """
    Define os quantitativos contratados para um projeto/designer.
    Acesso restrito a Gerência, Sócio e Admin.
    Payload: {email_investidor, mes, ano, projeto_id, cliente, criativos, videos, lp}
    """
    user_posicao = session.get("posicao", "")
    user_nivel = session.get("nivel_acesso", "")
    if user_posicao not in ("Gerência", "Sócio", "Coordenador") and user_nivel != "Admin":
        return jsonify({"error": "Acesso restrito."}), 403

    data = request.json or {}
    email = data.get("email_investidor")
    mes = data.get("mes")
    ano = data.get("ano")
    projeto_id = data.get("projeto_id")
    cliente_nome = data.get("cliente", "")

    if not all([email, mes, ano, projeto_id]):
        return jsonify({"error": "Campos obrigatórios: email_investidor, mes, ano, projeto_id"}), 400

    if int(ano) == 2026 and int(mes) in (2, 3):
        return jsonify({"error": "As entregas dos meses 02 e 03 de 2026 estão bloqueadas."}), 400

    try:
        with Session() as db:
            # Validação de Squad para Coordenador
            if user_posicao == "Coordenador":
                u_squad = session.get("squad")
                if not u_squad:
                    return jsonify({"error": "Coordenador sem Squad atribuída."}), 403
                target_user = db.query(Investidor).filter_by(email=email).first()
                if not target_user or target_user.squad != u_squad:
                    return jsonify({"error": "Acesso restrito à sua Squad."}), 403

            record = _get_or_create_entrega_record(db, email, int(mes), int(ano))
            lista = list(record.entregas_criativos or [])

            for categoria in ("criativos", "videos", "lp"):
                if categoria in data:
                    lista = update_contratados(lista, projeto_id, cliente_nome, categoria, data[categoria])

            record.entregas_criativos = lista
            db.commit()
            return jsonify({"ok": True, "entregas_criativos": lista})
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/criativa/entregas/entregues", methods=["PUT"])
@check_session
@check_access(["Designer", "WebDesigner"])
def update_criativa_entregues():
    """
    Atualiza a quantidade entregue de uma categoria para um projeto/designer.
    O membro do time só pode atualizar o próprio registro; Gerência/Sócio/Admin podem atualizar qualquer um.
    Payload: {email_investidor, mes, ano, projeto_id, cliente, categoria, valor}
    """
    data = request.json or {}
    email = data.get("email_investidor")
    mes = data.get("mes")
    ano = data.get("ano")
    projeto_id = data.get("projeto_id")
    cliente_nome = data.get("cliente", "")
    categoria = data.get("categoria")
    valor = data.get("valor", 0)

    if not all([email, mes, ano, projeto_id, categoria]):
        return jsonify({"error": "Campos obrigatórios: email_investidor, mes, ano, projeto_id, categoria"}), 400

    if int(ano) == 2026 and int(mes) in (2, 3):
        return jsonify({"error": "As entregas dos meses 02 e 03 de 2026 estão bloqueadas."}), 400

    # Bloqueia entregas em meses futuros
    hoje = dt.now()
    if int(ano) > hoje.year or (int(ano) == hoje.year and int(mes) > hoje.month):
        return jsonify({"error": "Não é permitido registrar entregas em meses futuros."}), 400

    # Time só pode editar o próprio registro
    user_email = session.get("email")
    user_posicao = session.get("posicao", "")
    user_nivel = session.get("nivel_acesso", "")
    is_high_level = user_posicao in ("Gerência", "Sócio", "Coordenador") or user_nivel == "Admin"
    if not is_high_level and user_email != email:
        return jsonify({"error": "Você só pode editar suas próprias entregas."}), 403

    categorias_validas = {"criativos", "videos", "lp"}
    if categoria not in categorias_validas:
        return jsonify({"error": f"Categoria inválida. Use: {', '.join(categorias_validas)}"}), 400

    try:
        with Session() as db:
            # Validação de Squad para Coordenador
            if user_posicao == "Coordenador" and user_email != email:
                u_squad = session.get("squad")
                if not u_squad:
                    return jsonify({"error": "Coordenador sem Squad atribuída."}), 403
                target_user = db.query(Investidor).filter_by(email=email).first()
                if not target_user or target_user.squad != u_squad:
                    return jsonify({"error": "Acesso restrito à sua Squad."}), 403

            record = _get_or_create_entrega_record(db, email, int(mes), int(ano))
            lista_atual = list(record.entregas_criativos or [])

            # Designer pode entregar acima do contratado — o "extra" não conta no MRR
            # (cap por categoria aplicado em _recalcular_mrr_por_entregas)
            if int(valor) < 0:
                return jsonify({"error": "Valor não pode ser negativo."}), 400

            lista = update_entregues(lista_atual, projeto_id, cliente_nome, categoria, valor)
            record.entregas_criativos = lista
            flag_modified(record, "entregas_criativos")
            db.commit()
            return jsonify({"ok": True, "entregas_criativos": lista})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/criativa/entregas/link", methods=["PUT"])
@check_session
@check_access(["Designer", "WebDesigner"])
def update_criativa_link():
    """
    Atualiza o link de criativos para um projeto/designer no JSONB.
    O membro do time só pode editar o próprio registro; Gerência/Sócio/Admin podem editar qualquer um.
    Payload: {email_investidor, mes, ano, projeto_id, cliente, link}
    """
    data = request.json or {}
    email = data.get("email_investidor")
    mes = data.get("mes")
    ano = data.get("ano")
    projeto_id = data.get("projeto_id")
    cliente_nome = data.get("cliente", "")
    link = data.get("link", "")

    if not all([email, mes, ano, projeto_id]):
        return jsonify({"error": "Campos obrigatórios: email_investidor, mes, ano, projeto_id"}), 400

    if int(ano) == 2026 and int(mes) in (2, 3):
        return jsonify({"error": "As entregas dos meses 02 e 03 de 2026 estão bloqueadas."}), 400

    user_email = session.get("email")
    user_posicao = session.get("posicao", "")
    user_nivel = session.get("nivel_acesso", "")
    is_high_level = user_posicao in ("Gerência", "Sócio", "Coordenador") or user_nivel == "Admin"
    if not is_high_level and user_email != email:
        return jsonify({"error": "Você só pode editar suas próprias entregas."}), 403

    try:
        with Session() as db:
            record = _get_or_create_entrega_record(db, email, int(mes), int(ano))
            lista = update_link_criativo(
                list(record.entregas_criativos or []),
                projeto_id, cliente_nome, link
            )
            record.entregas_criativos = lista
            db.commit()
            return jsonify({"ok": True})
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


# ─── APIs OPERAÇÃO ───────────────────────────────────────────────────────────

@app.route("/api/operacao/tarefas/<int:pipefy_id>", methods=["GET"])
@check_session
@check_access(["Account", "Gestor de Tráfego", "Cientista"])
def get_tarefas(pipefy_id):
    """Lê tarefas/metas da tabela operacao.entregas (UNICA tabela)."""
    tipo = request.args.get("tipo", "semanal")
    referencia = request.args.get("referencia", "")
    try:
        # Extrair mes/ano da referência
        mes, ano = None, None
        if referencia and "-M" in referencia:
            parts = referencia.split("-M")
            ano, mes = int(parts[0]), int(parts[1])
        else:
            now = dt.now()
            mes, ano = now.month, now.year

        snap = _operacao_get_snapshot(pipefy_id, mes, ano) or {}

        if tipo == "goal_snapshot":
            metas = snap.get("metas") or {}
            if not metas:
                return jsonify([])
            # Frontend espera: array com {id, descricao (JSON string), concluida, referencia}
            return jsonify([{
                "id": 1,
                "descricao": json.dumps(metas, ensure_ascii=False),
                "concluida": bool(metas.get("concluida", False)),
                "referencia": referencia or f"{ano}-M{mes:02d}",
            }])

        # Tarefas semanais/quarter — não usadas no novo modelo de tabela única
        return jsonify([])
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/tarefas", methods=["POST"])
@check_session
@check_access(["Account", "Gestor de Tráfego", "Cientista"])
def save_tarefa():
    """Salva metas (goal_snapshot) APENAS na tabela operacao.entregas.metas."""
    data = request.json or {}
    email = session.get("email")
    pipefy_id = data.get("pipefy_id")
    tipo = data.get("tipo")
    referencia = data.get("referencia", "")
    descricao = data.get("descricao")

    try:
        # Determinar mes/ano — priorizar valores explícitos enviados pelo frontend
        mes = data.get("mes")
        ano = data.get("ano")
        if mes is not None and ano is not None:
            mes, ano = int(mes), int(ano)
        elif referencia and "-M" in referencia:
            parts = referencia.split("-M")
            ano, mes = int(parts[0]), int(parts[1])
        elif referencia and "-W" in referencia and tipo == "semanal":
            y, w = map(int, referencia.split("-W"))
            d = dt.fromisocalendar(y, w, 1)
            mes, ano = d.month, d.year
        else:
            now = dt.now()
            mes, ano = now.month, now.year

        # Tratamento por tipo
        if tipo == "semanal":
            # Salva na seção tarefas_semanais do snapshot
            tarefa_item = {
                "descricao": descricao,
                "referencia": referencia,
                "criado_por": email,
                "data": dt.now().strftime("%Y-%m-%d")
            }
            _operacao_save_section(pipefy_id, mes, ano, "tarefas_semanais", tarefa_item, append=True)
            _sync_metrica_entregas_operacao(email, pipefy_id, mes, ano)
            return jsonify({"status": "success", "id": 1})

        if tipo != "goal_snapshot" and not data.get("id"):
            # Outros tipos (ex: quarter antigo) não persistem
            return jsonify({"status": "success", "id": 1})

        # Carregar metas atuais
        metas = snap.get("metas") or {}
        return jsonify({"status": "success", "id": 1})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/tarefas", methods=["DELETE"])
@check_session
@check_access(["Account", "Gestor de Tráfego"])
def delete_tarefa_manual():
    """Remove o último registro manual do Planner Monday."""
    data = request.json or {}
    pipefy_id = data.get("pipefy_id")
    if not pipefy_id:
        return jsonify({"error": "pipefy_id obrigatório"}), 400

    # Priorizar mes/ano explícitos enviados pelo frontend
    mes = data.get("mes")
    ano = data.get("ano")
    if mes is None or ano is None:
        referencia = data.get("referencia", "")
        if referencia and "-W" in referencia:
            try:
                y, w = map(int, referencia.split("-W"))
                d = dt.fromisocalendar(y, w, 1)
                mes, ano = d.month, d.year
            except Exception:
                now = dt.now()
                mes, ano = now.month, now.year
        else:
            now = dt.now()
            mes, ano = now.month, now.year
    else:
        mes, ano = int(mes), int(ano)
    email = session.get("email")

    try:
        snap = _operacao_get_snapshot(pipefy_id, mes, ano)
        lst = list(snap["tarefas_semanais"]) if snap and "tarefas_semanais" in snap else []
        
        if not lst:
            # Fallback: decrementar MetricaMensal diretamente (fonte da /criativa)
            with Session() as _db:
                _metrica = _db.query(MetricaMensal).filter_by(
                    email_investidor=email, mes=int(mes), ano=int(ano)
                ).first()
                if _metrica and _metrica.entregas_operacao:
                    for _entry in _metrica.entregas_operacao:
                        if str(_entry.get("projeto_id")) == str(pipefy_id):
                            for _ee in _entry.get("entregas", []):
                                if _ee.get("nome") == "planner_monday" and _ee.get("entregues", 0) > 0:
                                    _ee["entregues"] -= 1
                                    flag_modified(_metrica, "entregas_operacao")
                                    _db.commit()
                                    return jsonify({"status": "success", "source": "metrica"})
                            break
            return jsonify({"error": "Nenhum registro para remover"}), 400

        # Remove a última tarefa (decremento)
        del lst[-1]

        with engine.begin() as conn:
            snap["tarefas_semanais"] = lst
            conn.execute(text(
                "UPDATE plataforma_geral.operacao SET entregas = CAST(:ent AS jsonb) "
                "WHERE id_projeto = :id AND mes = :mes AND ano = :ano"
            ), {"ent": json.dumps(snap, ensure_ascii=False), "id": str(pipefy_id), "mes": mes, "ano": ano})

        _sync_metrica_entregas_operacao(email, pipefy_id, mes, ano)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

        if descricao:
            # Salvar/sobrescrever metas com nova descricao (JSON string)
            try:
                metas = json.loads(descricao)
            except Exception:
                metas = {"raw": descricao}

        # Toggle de conclusão (sem descricao, só concluida)
        if "concluida" in data and not descricao:
            metas["concluida"] = bool(data.get("concluida"))

        if pipefy_id:
            _operacao_save_section(pipefy_id, mes, ano, "metas", metas, append=False)
            _sync_metrica_entregas_operacao(email, pipefy_id, mes, ano)

        return jsonify({"status": "success", "id": 1})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─── APIs ENTREGAS OPERAÇÃO (JSONB) ──────────────────────────────────────────

@app.route("/api/operacao/entregas-op/<email>/<int:mes>/<int:ano>", methods=["GET"])
@check_session
@check_access(["Account", "Gestor de Tráfego"])
def get_entregas_operacao(email, mes, ano):
    user_email = session.get("email")
    user_posicao = session.get("posicao", "")
    user_nivel = session.get("nivel_acesso", "")
    is_high_level = user_posicao in ("Gerência", "Sócio", "Coordenador") or user_nivel == "Admin"
    if not is_high_level and user_email != email:
        return jsonify({"error": "Acesso restrito"}), 403
    try:
        _sync_entregas_operacao_periodo_fast(email, mes, ano)
        with Session() as db:
            record = db.query(MetricaMensal).filter_by(
                email_investidor=email, mes=mes, ano=ano
            ).first()
            return jsonify(record.entregas_operacao if record else [])
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


def _sync_snapshot_entrega_count(projeto_id, mes, ano, nome_entrega, valor, email, cliente_nome=""):
    """Espelha contagem de entrega definida via /criativa no snapshot da operacao.
    Apenas para tipos onde o snapshot armazena flags/links simples ou tarefas semanais.
    Tipos array (checkin_semanal, otimizacoes) são preservados no snapshot real;
    a contagem alternativa vem via fallback MetricaMensal em get_monthly_deliveries."""
    _snap = _operacao_get_snapshot(projeto_id, mes, ano)
    if _snap is None:
        _snap = {}
    if nome_entrega == "planner_monday":
        _target = min(valor, 4)
        _current = list(_snap.get("tarefas_semanais") or [])
        if _target > len(_current):
            for _ in range(_target - len(_current)):
                _current.append({"descricao": "Registro via criativa",
                                 "criado_por": email,
                                 "data": dt.now().strftime("%Y-%m-%d")})
        elif _target < len(_current):
            del _current[_target:]
        _snap["tarefas_semanais"] = _current
    elif nome_entrega == "plano_de_midia":
        if valor >= 1:
            _snap["plano_midia"] = {"budget_total": 0, "planos": [
                {"canal": "Manual", "nome_campanha": "Registro via criativa",
                 "%_budget": 0, "R$_budget": 0, "budget_dia": 0}]}
        else:
            _snap["plano_midia"] = {"budget_total": 0, "planos": []}
    elif nome_entrega in ("kpis", "forecasting", "relatorio_account", "relatorio_gt", "relatorio_mensal"):
        _s = dict(_snap.get(nome_entrega) or {})
        _s["link"] = "manual" if valor >= 1 else ""
        _snap[nome_entrega] = _s
    with engine.begin() as _conn:
        _res = _conn.execute(text(
            "UPDATE plataforma_geral.operacao SET entregas = CAST(:ent AS jsonb) "
            "WHERE id_projeto = :id AND mes = :mes AND ano = :ano"
        ), {"ent": json.dumps(_snap), "id": str(projeto_id), "mes": mes, "ano": ano})
        if _res.rowcount == 0:
            _conn.execute(text(
                "INSERT INTO plataforma_geral.operacao (id_projeto, nome, mes, ano, entregas) "
                "VALUES (:id, :nome, :mes, :ano, CAST(:ent AS jsonb))"
            ), {"id": str(projeto_id), "nome": cliente_nome,
                "mes": mes, "ano": ano, "ent": json.dumps(_snap)})


@app.route("/api/operacao/entregas-op/entregues", methods=["PUT"])
@check_session
@check_access(["Account", "Gestor de Tráfego"])
def update_entregas_operacao_entregues():
    data = request.json or {}
    email = data.get("email_investidor")
    mes = data.get("mes")
    ano = data.get("ano")
    projeto_id = data.get("projeto_id")
    cliente_nome = data.get("cliente", "")
    responsavel = data.get("responsavel", "account")
    nome_entrega = data.get("nome_entrega")
    tipo_entrega = data.get("tipo_entrega")
    valor = data.get("valor", 0)

    if not all([email, mes, ano, projeto_id, nome_entrega, tipo_entrega]):
        return jsonify({"error": "Campos obrigatórios: email_investidor, mes, ano, projeto_id, nome_entrega, tipo_entrega"}), 400

    if int(ano) == 2026 and int(mes) in (2, 3):
        return jsonify({"error": "As entregas dos meses 02 e 03 de 2026 estão bloqueadas."}), 400

    hoje = dt.now()
    if int(ano) > hoje.year or (int(ano) == hoje.year and int(mes) > hoje.month):
        return jsonify({"error": "Não é permitido registrar entregas em meses futuros."}), 400

    user_email = session.get("email")
    user_posicao = session.get("posicao", "")
    user_nivel = session.get("nivel_acesso", "")
    is_high_level = user_posicao in ("Gerência", "Sócio", "Coordenador") or user_nivel == "Admin"
    if not is_high_level and user_email != email:
        return jsonify({"error": "Você só pode editar suas próprias entregas."}), 403

    if responsavel not in ("account", "gt", "cientista"):
        return jsonify({"error": "responsavel inválido. Use: account, gt ou cientista"}), 400

    try:
        with Session() as db:
            # ── VALIDAÇÃO DE CONSISTÊNCIA DE TIPO DE ENTREGA (E8) ──────────
            # Busca vínculo para verificar status de cientista
            inv_proj = db.query(InvestidorProjeto).filter_by(
                email_investidor=email, pipefy_id_projeto=projeto_id
            ).first()
            is_cientista = inv_proj.cientista if inv_proj else False

            if is_cientista:
                # Se é cientista, forçamos o tipo e responsavel corretos
                responsavel = "cientista"
                tipo_entrega = "CIENTISTA"
            else:
                # Se não é cientista, validamos contra o cargo base
                investidor = db.query(Investidor).filter_by(email=email).first()
                if not investidor:
                    return jsonify({"error": "Investidor não encontrado."}), 404
                
                cargo_base = (investidor.funcao or "").strip()
                expected = "gt" if cargo_base == "Gestor de Tráfego" else "account"
                
                if tipo_entrega.lower() != expected:
                    return jsonify({
                        "error": f"Inconsistência: tipo_entrega '{tipo_entrega}' inválido para investidor '{cargo_base}' (não cientista neste projeto)."
                    }), 400
                
                # Normaliza para o padrão esperado
                tipo_entrega = expected
                responsavel = expected
            # ──────────────────────────────────────────────────────────────

            # Validação de Squad para Coordenador
            if user_posicao == "Coordenador" and user_email != email:
                u_squad = session.get("squad")
                if not u_squad:
                    return jsonify({"error": "Coordenador sem Squad atribuída."}), 403
                target_user = db.query(Investidor).filter_by(email=email).first()
                if not target_user or target_user.squad != u_squad:
                    return jsonify({"error": "Acesso restrito à sua Squad."}), 403

            record = _get_or_create_entrega_record(db, email, int(mes), int(ano))
            lista = _update_entrega_op_entregues(
                list(record.entregas_operacao or []),
                projeto_id, cliente_nome, responsavel, nome_entrega, tipo_entrega, int(valor)
            )
            record.entregas_operacao = lista
            flag_modified(record, "entregas_operacao")
            _recalcular_mrr_por_entregas(db, record)

            # Sincronizar snapshot quando /criativa altera qualquer entrega
            _sync_snapshot_entrega_count(str(projeto_id), int(mes), int(ano),
                                         nome_entrega, int(valor), email, cliente_nome)

            db.commit()
            return jsonify({"ok": True, "entregas_operacao": lista})
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/entregas-op/links", methods=["PUT"])
@check_session
@check_access(["Account", "Gestor de Tráfego", "Gerência", "Sócio"])
def update_entregas_operacao_links():
    data = request.json or {}
    email = data.get("email_investidor")
    mes = data.get("mes")
    ano = data.get("ano")
    projeto_id = data.get("projeto_id")
    cliente_nome = data.get("cliente", "")
    responsavel = data.get("responsavel", "")
    link_relatorio = data.get("link_relatorio")
    link_kpi = data.get("link_kpi")
    link_forecast = data.get("link_forecast")

    if not all([email, mes, ano, projeto_id]):
        return jsonify({"error": "Campos obrigatórios: email_investidor, mes, ano, projeto_id"}), 400

    user_email = session.get("email")
    user_posicao = session.get("posicao", "")
    user_nivel = session.get("nivel_acesso", "")
    is_high_level = user_posicao in ("Gerência", "Sócio", "Coordenador") or user_nivel == "Admin"
    if not is_high_level and user_email != email:
        return jsonify({"error": "Você só pode editar suas próprias entregas."}), 403

    try:
        with Session() as db:
            responsavel = _infer_entregas_op_responsavel(db, email, int(projeto_id), responsavel)
            record = _get_or_create_entrega_record(db, email, int(mes), int(ano))
            lista = _update_entrega_op_links(
                list(record.entregas_operacao or []),
                projeto_id, cliente_nome, responsavel,
                link_relatorio, link_kpi, link_forecast
            )
            record.entregas_operacao = lista
            flag_modified(record, "entregas_operacao")
            _sync_snapshot_links_from_entregas_op(
                db, int(projeto_id), int(mes), int(ano), responsavel,
                link_relatorio=link_relatorio,
                link_kpi=link_kpi,
                link_forecast=link_forecast,
            )
            db.commit()
        _sync_metrica_entregas_operacao(email, int(projeto_id), int(mes), int(ano))
        with Session() as db:
            record = db.query(MetricaMensal).filter_by(
                email_investidor=email, mes=int(mes), ano=int(ano)
            ).first()
            return jsonify({"ok": True, "entregas_operacao": record.entregas_operacao if record else lista})
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500


# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/operacao/entregas/<int:pipefy_id>/<int:mes>/<int:ano>", methods=["GET"])
@check_session
@check_access(["Account", "Gestor de Tráfego"])
def get_entregas(pipefy_id, mes, ano):
    email = session.get("email")
    try:
        with Session() as db:
            entrega = db.query(OperacaoEntregaMensal).filter_by(
                investidor_email=email, projeto_pipefy_id=pipefy_id, mes=mes, ano=ano
            ).first()
            if not entrega:
                return jsonify({
                    "entrega_1": False, "entrega_2": False, "entrega_3": False, "entrega_4": False,
                    "percentual": 0
                })
            return jsonify({
                "entrega_1": entrega.entrega_1,
                "entrega_2": entrega.entrega_2,
                "entrega_3": entrega.entrega_3,
                "entrega_4": entrega.entrega_4,
                "percentual": float(entrega.percentual_calculado or 0)
            })
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: MONTHLY DELIVERIES (ENTREGAS AUTOMÁTICAS – READ ONLY)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/criativa/op-deliveries/<email>/<int:mes>/<int:ano>", methods=["GET"])
@check_session
def get_op_deliveries_coord(email, mes, ano):
    """Retorna status das entregas mensais de um Account/GT para coordenadores."""
    posicao = session.get("posicao", "").strip()
    nivel   = session.get("nivel_acesso", "").strip()
    if posicao not in ("Gerência", "Sócio", "Coordenador") and nivel != "Admin":
        return jsonify({"error": "Acesso restrito"}), 403
    try:
        with Session() as db:
            # Validação de Squad para Coordenador
            if posicao == "Coordenador":
                u_squad = session.get("squad")
                if not u_squad:
                    return jsonify({"error": "Coordenador sem Squad atribuída."}), 403
                target_user = db.query(Investidor).filter_by(email=email).first()
                if not target_user or target_user.squad != u_squad:
                    return jsonify({"error": "Acesso restrito à sua Squad."}), 403

            entregas = db.query(MonthlyDelivery).filter_by(
                email=email, month=mes, year=ano
            ).all()
            result = {}
            for e in entregas:
                pid = str(e.client_id)
                if pid not in result:
                    result[pid] = {}
                result[pid][e.delivery_type] = e.status
            return jsonify(result)
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/criativa/op-deliveries", methods=["PUT"])
@check_session
def update_op_delivery_coord():
    """Permite coordenador marcar/desmarcar entrega manualmente."""
    posicao = session.get("posicao", "").strip()
    nivel   = session.get("nivel_acesso", "").strip()
    if posicao not in ("Gerência", "Sócio", "Coordenador") and nivel != "Admin":
        return jsonify({"error": "Acesso restrito"}), 403
    data = request.get_json()
    email         = data.get("email")
    client_id     = data.get("client_id")
    delivery_type = data.get("delivery_type")
    mes           = data.get("mes")
    ano           = data.get("ano")
    status        = data.get("status")  # 'completed' | 'pending'
    if not all([email, client_id, delivery_type, mes, ano, status in ("completed", "pending")]):
        return jsonify({"error": "Dados inválidos"}), 400
    try:
        with Session() as db:
            # Validação de Squad para Coordenador
            if posicao == "Coordenador":
                u_squad = session.get("squad")
                if not u_squad:
                    return jsonify({"error": "Coordenador sem Squad atribuída."}), 403
                target_user = db.query(Investidor).filter_by(email=email).first()
                if not target_user or target_user.squad != u_squad:
                    return jsonify({"error": "Acesso restrito à sua Squad."}), 403

            entry = db.query(MonthlyDelivery).filter_by(
                email=email, client_id=int(client_id),
                delivery_type=delivery_type, month=mes, year=ano
            ).first()
            if not entry:
                return jsonify({"error": "Entrega não encontrada"}), 404
            entry.status = status
            entry.completed_at = __import__('datetime').datetime.now() if status == 'completed' else None
            db.commit()
        return jsonify({"status": "ok"})
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/monthly-deliveries/<int:pipefy_id>/<int:mes>/<int:ano>", methods=["GET"])
@check_session
def get_monthly_deliveries(pipefy_id, mes, ano):
    """Calcula entregas concluídas baseado no snapshot + fallback MetricaMensal."""
    try:
        email = session.get("email")
        if email:
            _sync_legacy_links_for_project(email, pipefy_id, mes, ano)

        snap = _operacao_get_snapshot(pipefy_id, mes, ano)
        if not snap:
            snap = {}

        # Ler MetricaMensal do usuário atual como fallback para /criativa
        metrica_counts = {}
        if email:
            try:
                with Session() as _db:
                    _rec = _db.query(MetricaMensal).filter_by(
                        email_investidor=email, mes=int(mes), ano=int(ano)
                    ).first()
                    if _rec and _rec.entregas_operacao:
                        for _entry in _rec.entregas_operacao:
                            if str(_entry.get("projeto_id")) == str(pipefy_id):
                                for _ee in _entry.get("entregas", []):
                                    metrica_counts[_ee.get("nome")] = _ee.get("entregues", 0)
                                break
            except Exception as e:
                print(f"[monthly-deliveries] erro MetricaMensal: {e}")

        def _m(metrica_nome, snap_count):
            return max(snap_count, metrica_counts.get(metrica_nome, 0))

        deliveries = []
        idx = 0

        # Dados do snapshot
        planos = (snap.get("plano_midia") or {}).get("planos") or []
        otims = snap.get("otimizacoes") or []
        checkins = snap.get("checkin_semanal") or []
        tarefas_semanais = snap.get("tarefas_semanais") or []
        kpis_link = (snap.get("kpis") or {}).get("link") or ""
        forecasting_link = (snap.get("forecasting") or {}).get("link") or ""
        relatorio_link = (snap.get("relatorio_mensal") or {}).get("link") or ""
        relatorio_acc_link = (snap.get("relatorio_account") or {}).get("link") or ""
        relatorio_gt_link = (snap.get("relatorio_gt") or {}).get("link") or ""

        # === PLANO DE MÍDIA — meta 1 ===
        cnt = _m("plano_de_midia", 1 if planos else 0)
        idx += 1
        deliveries.append({
            "id": idx, "role": "Gestor de Tráfego",
            "delivery_type": "plano_midia",
            "status": "completed" if cnt >= 1 else "pending",
            "count": min(cnt, 1),
            "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
        })

        # === OTIMIZAÇÕES — meta 4 ===
        cnt = _m("documento_de_otimizacao", len(otims))
        idx += 1
        deliveries.append({
            "id": idx, "role": "Gestor de Tráfego",
            "delivery_type": "otimizacao",
            "status": "completed" if cnt >= 4 else ("partial" if cnt > 0 else "pending"),
            "count": min(cnt, 4),
            "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
        })

        # === CHECK-IN / CSAT — meta 4 ===
        cnt = _m("csat_checkin", len(checkins))
        idx += 1
        deliveries.append({
            "id": idx, "role": "Account",
            "delivery_type": "checkin",
            "status": "completed" if cnt >= 4 else ("partial" if cnt > 0 else "pending"),
            "count": min(cnt, 4),
            "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
        })

        # === FORECASTING — meta 1 ===
        cnt = _m("forecasting", 1 if forecasting_link else 0)
        idx += 1
        deliveries.append({
            "id": idx, "role": "Account",
            "delivery_type": "forecasting",
            "status": "completed" if cnt >= 1 else "pending",
            "count": min(cnt, 1),
            "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
        })

        # === KPIs — meta 1 ===
        cnt = _m("kpis", 1 if kpis_link else 0)
        idx += 1
        deliveries.append({
            "id": idx, "role": "Gestor de Tráfego",
            "delivery_type": "kpis",
            "status": "completed" if cnt >= 1 else "pending",
            "count": min(cnt, 1),
            "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
        })

        # === RELATÓRIO MENSAL — meta 1 ===
        has_report = relatorio_link or relatorio_acc_link or relatorio_gt_link
        cnt = _m("relatorio_mensal", 1 if has_report else 0)
        idx += 1
        deliveries.append({
            "id": idx, "role": "Gestor de Tráfego",
            "delivery_type": "relatorio_mensal",
            "status": "completed" if cnt >= 1 else "pending",
            "count": min(cnt, 1),
            "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
        })

        cnt = _m("relatorio_gt", 1 if (relatorio_gt_link or relatorio_link) else 0)
        idx += 1
        deliveries.append({
            "id": idx, "role": "Gestor de Tráfego",
            "delivery_type": "relatorio_gt",
            "status": "completed" if cnt >= 1 else "pending",
            "count": min(cnt, 1),
            "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
        })

        cnt = _m("relatorio_account", 1 if (relatorio_acc_link or relatorio_link) else 0)
        idx += 1
        deliveries.append({
            "id": idx, "role": "Account",
            "delivery_type": "relatorio_account",
            "status": "completed" if cnt >= 1 else "pending",
            "count": min(cnt, 1),
            "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
        })

        # === PLANNER MONDAY — meta 4 ===
        cnt = _m("planner_monday", len(tarefas_semanais))
        idx += 1
        deliveries.append({
            "id": idx, "role": "Account",
            "delivery_type": "planner_monday",
            "status": "completed" if cnt >= 4 else ("partial" if cnt > 0 else "pending"),
            "count": min(cnt, 4),
            "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
        })

        return jsonify(deliveries)
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/entregas", methods=["POST"])
@check_session
def block_manual_entrega():
    """Marcação manual de entregas foi desabilitada. Entregas são 100% automáticas."""
    return jsonify({"error": "Marcação manual de entregas não é permitida. As entregas são geradas automaticamente pelo sistema."}), 403

@app.route("/api/remuneracao/processar")
@check_session
def processar_remuneracao():
    """Endpoint para processar métricas do mês atual."""
    from datetime import datetime as dt
    try:
        ProjetoParticipacaoService.sincronizar_remuneracao(dt.now().month, dt.now().year)
        calcular_metricas_mensais(dt.now().month, dt.now().year)
        return jsonify({"status": "success", "message": "Métricas processadas."})

    except Exception as e:
        print(f"Erro ao processar remuneracao: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/remuneracao/recalcular-historico")
@check_session
@check_access(["Gerência"])
def recalcular_historico_remuneracao():
    """Recalcula todos os meses presentes no banco. Apenas Gerência."""
    try:
        with Session() as db:
            periodos = db.query(
                MetricaMensal.mes, MetricaMensal.ano
            ).distinct().order_by(MetricaMensal.ano, MetricaMensal.mes).all()

        resultados = []
        for mes, ano in periodos:
            try:
                ProjetoParticipacaoService.sincronizar_remuneracao(mes, ano)
                calcular_metricas_mensais(mes, ano)
                resultados.append({"mes": mes, "ano": ano, "status": "ok"})
            except Exception as e:
                resultados.append({"mes": mes, "ano": ano, "status": "erro", "detalhe": str(e)})

        return jsonify({"status": "success", "periodos": resultados})
    except Exception as e:
        print(f"Erro ao recalcular histórico: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/remuneracao/recalcular-investidor/<email>/<int:mes>/<int:ano>", methods=["POST"])
@check_session
def recalcular_investidor(email, mes, ano):
    """Recalcula MRR de um investidor específico para um mês/ano.
    Chamado pelo frontend APÓS o lote de marcações de entrega para evitar
    N recálculos simultâneos e inconsistências de concorrência."""
    try:
        with Session() as db:
            if mes > dt.now().month and ano >= dt.now().year:
                return jsonify({"error": "Mês futuro não permitido."}), 400

            record = db.query(MetricaMensal).filter_by(
                email_investidor=email, mes=mes, ano=ano
            ).with_for_update().first()

            if not record:
                return jsonify({"error": "Registro não encontrado. Crie entregas primeiro."}), 404

            _recalcular_mrr_por_entregas(db, record)
            db.commit()
            db.refresh(record)

            return jsonify({
                "ok": True,
                "remu": {
                    "month_year": f"{record.mes:02d}/{record.ano}",
                    "mes": record.mes,
                    "ano": record.ano,
                    "mrr": float(record.fixo_mrr_atual or 0),
                    "mrr_bruto_entregue": float(record.fixo_mrr_entrega or 0),
                    "mrr_total": float(record.fixo_mrr_projeto_total or 0),
                    "mrr_esperado": float(record.fixo_mrr_esperado or 0),
                    "mrr_teto": float(record.fixo_mrr_teto or 0),
                    "churn": float(record.calc_churn_real_percentual or 0),
                    "churn_rs": float(record.fixo_churn_atual or 0),
                    "variable_brl": float(record.calc_variavel_total or 0),
                    "total_brl": max(float(record.calc_remuneracao_total or 0), float(record.fixo_remuneracao_minima or 0)),
                    "rem_min": float(record.fixo_remuneracao_minima or 0),
                    "rem_max": float(record.fixo_remuneracao_maxima or 0),
                    "fixo": float(record.fixo_remuneracao_fixa or 0),
                }
            })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# AUXILIARES DE AUTOMAÇÃO DE ENTREGAS
# ─────────────────────────────────────────────────────────────────────────────

def sync_mrr_vinculos(db, pipefy_id, valor_contribuicao):
    """Sincroniza o valor de contribuição em todos os vínculos do projeto."""
    vinculos = db.query(InvestidorProjeto).filter_by(pipefy_id_projeto=pipefy_id).all()
    for v in vinculos:
        v.fee_contribuicao = valor_contribuicao

def atualizar_entregas_automaticas(db, pipefy_id, mes, ano, investidor_email):
    """
    Lógica de Automação de Entregas para Gestores de Tráfego:
    1 - Plano de Mídia: Existe algum plano salvo no mês/ano?
    2 - Otimizações: Existem pelo menos 4 otimizações no mês/ano?
    3 - Setup/Relatório: (Pode ser estendido para verificar tasks específicas futuramente)
    """
    # 1. Verificar Plano de Mídia
    plano_existe = db.query(OperacaoPlanoMidia).filter_by(
        projeto_pipefy_id=pipefy_id, mes=mes, ano=ano
    ).first() is not None

    # 2. Verificar 4 Otimizações
    # (Simplificação: pegamos otimizações dentro do mês/ano da data_otimizacao)
    # Nota: Precisamos filtrar pela data no banco.
    from sqlalchemy import extract
    count_otimizacoes = db.query(OperacaoOtimizacao).filter(
        OperacaoOtimizacao.projeto_pipefy_id == pipefy_id,
        extract('month', OperacaoOtimizacao.data_otimizacao) == mes,
        extract('year', OperacaoOtimizacao.data_otimizacao) == ano
    ).count()

    # Busca ou cria registro de entrega
    entrega = db.query(OperacaoEntregaMensal).filter_by(
        investidor_email=investidor_email, projeto_pipefy_id=pipefy_id, mes=mes, ano=ano
    ).first()

    if not entrega:
        projeto = db.get(Projeto, pipefy_id)
        fee = float(projeto.fee or 0) if projeto else 0
        entrega = OperacaoEntregaMensal(
            investidor_email=investidor_email, projeto_pipefy_id=pipefy_id, mes=mes, ano=ano,
            valor_fee_original=fee
        )
        db.add(entrega)

    # Marca entregas automáticas
    entrega.entrega_1 = plano_existe
    entrega.entrega_2 = (count_otimizacoes >= 4)
    # Entrega 3 e 4 permanecem manuais por enquanto ou via tasks (pode evoluir)

    # Recalcula percentual e MRR
    count = sum([1 for i in range(1, 5) if getattr(entrega, f"entrega_{i}")])
    entrega.percentual_calculado = count * 0.25
    entrega.valor_contribuicao_mrr = float(entrega.percentual_calculado) * float(entrega.valor_fee_original)

    # Sincroniza vínculos
    sync_mrr_vinculos(db, pipefy_id, entrega.valor_contribuicao_mrr)
    
    db.commit()
    return recalculate_investor_mrr(db, investidor_email, mes, ano)

# ─── APIs NOVAS (PLANO, OTIMIZAÇÃO, CHECKIN) ──────────────────────────────────

@app.route("/api/operacao/plano-midia", methods=["POST"])
@check_session
@check_access(["Gestor de Tráfego", "Cientista", "Gerência", "Account", "Desenvolvedor"])
def save_plano_midia():
    """Salva plano de mídia APENAS na tabela operacao.entregas.plano_midia."""
    data = request.json or {}
    email = session.get("email")
    pipefy_id = data.get("pipefy_id")
    mes = data.get("mes")
    ano = data.get("ano")
    dados = data.get("dados_plano", {})

    print(f"\n{'='*70}")
    print(f"[plano-midia POST] email={email} projeto={pipefy_id} mes={mes} ano={ano}")
    print(f"[plano-midia POST] dados recebidos: {json.dumps(dados, ensure_ascii=False)[:200]}")

    # Diagnóstico ANTES do save
    try:
        with engine.connect() as c:
            antes = c.execute(text(
                "SELECT COUNT(*) FROM plataforma_geral.operacao WHERE id_projeto = :id"
            ), {"id": str(pipefy_id)}).scalar()
            print(f"[plano-midia POST] linhas existentes na operacao para projeto {pipefy_id}: {antes}")
    except Exception as e:
        print(f"[plano-midia POST] ERRO ao contar antes: {e}")
        return jsonify({"error": f"DB connection error: {e}"}), 500

    plano_snap = {
        "budget_total": dados.get("budget_total", 0),
        "planos": [
            {
                "canal": c.get("canal", ""),
                "nome_campanha": c.get("campanhas", ""),
                "%_budget": c.get("percent_budget", 0),
                "R$_budget": c.get("budget", 0),
                "budget_dia": c.get("budget_dia", 0),
            }
            for c in dados.get("canais", [])
        ],
    }

    ok = _operacao_save_section(pipefy_id, mes, ano, "plano_midia", plano_snap, append=False)
    if not ok:
        return jsonify({"error": "Falha ao salvar na tabela operacao", "saved": False}), 500

    # Diagnóstico DEPOIS do save
    snap_atual = _operacao_get_snapshot(pipefy_id, mes, ano)
    with engine.connect() as c:
        depois = c.execute(text(
            "SELECT COUNT(*) FROM plataforma_geral.operacao WHERE id_projeto = :id"
        ), {"id": str(pipefy_id)}).scalar()
        print(f"[plano-midia POST] linhas APOS save: {depois}")

    _sync_metrica_entregas_operacao(email, pipefy_id, mes, ano)
    print(f"[plano-midia POST] FIM - retornando snapshot")
    print(f"{'='*70}\n")

    return jsonify({
        "status": "success",
        "saved": True,
        "rows_total_for_project": depois,
        "snapshot": snap_atual,
    })


@app.route("/api/operacao/planos-midia/<int:pipefy_id>", methods=["GET"])
@check_session
def get_plano_midia_historico(pipefy_id):
    """Retorna o histórico de planos de mídia para um projeto em todos os meses."""
    try:
        with Session() as db:
            from sqlalchemy import text
            snaps = db.execute(text(
                "SELECT mes, ano, entregas FROM plataforma_geral.operacao "
                "WHERE id_projeto = :id_projeto ORDER BY ano DESC, mes DESC"
            ), {"id_projeto": str(pipefy_id)}).fetchall()
            
            historico = []
            for s in snaps:
                entregas = s.entregas or {}
                if "plano_midia" in entregas and entregas["plano_midia"].get("planos"):
                    plano = entregas["plano_midia"]
                    historico.append({
                        "mes": s.mes,
                        "ano": s.ano,
                        "budget_total": plano.get("budget_total", 0),
                        "canais": [
                            {
                                "canal": p.get("canal", ""),
                                "campanhas": p.get("nome_campanha", ""),
                                "percent_budget": p.get("%_budget", 0),
                                "budget": p.get("R$_budget", 0),
                                "budget_dia": p.get("budget_dia", 0),
                            }
                            for p in plano.get("planos", [])
                        ]
                    })
            return jsonify(historico)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/plano-midia/<int:pipefy_id>/<int:mes>/<int:ano>", methods=["GET"])
@check_session
@check_access(["Account", "Gestor de Tráfego", "Cientista", "Desenvolvedor"])
def get_plano_midia(pipefy_id, mes, ano):
    """Lê plano de mídia da tabela operacao.entregas.plano_midia."""
    try:
        snap = _operacao_get_snapshot(pipefy_id, mes, ano)
        if not snap:
            return jsonify(None)
        plano = snap.get("plano_midia") or {}
        if not plano.get("planos"):
            return jsonify(None)

        return jsonify({
            "id": pipefy_id,
            "dados_plano": {
                "budget_total": plano.get("budget_total", 0),
                "canais": [
                    {
                        "canal": p.get("canal", ""),
                        "campanhas": p.get("nome_campanha", ""),
                        "percent_budget": p.get("%_budget", 0),
                        "budget": p.get("R$_budget", 0),
                        "budget_dia": p.get("budget_dia", 0),
                    }
                    for p in plano.get("planos", [])
                ],
            },
            "created_at": None,
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/test-db", methods=["GET"])
@check_session
def test_operacao_db():
    """Diagnóstico: tenta inserir e deletar uma linha de teste na tabela operacao."""
    import traceback
    try:
        with Session() as db:
            db.execute(text(
                "INSERT INTO plataforma_geral.operacao (mes, ano, nome, id_projeto, entregas) "
                "VALUES (1, 1999, 'TESTE_DIAGNOSTICO', 'TESTE_ID', '{\"ok\":true}'::jsonb)"
            ))
            db.execute(text(
                "DELETE FROM plataforma_geral.operacao WHERE id_projeto = 'TESTE_ID' AND ano = 1999"
            ))
            db.commit()
        return jsonify({"ok": True, "msg": "INSERT e DELETE na tabela operacao funcionaram."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/operacao/snapshot/<int:pipefy_id>/<int:mes>/<int:ano>", methods=["GET"])
@check_session
def get_operacao_snapshot(pipefy_id, mes, ano):
    """Retorna o JSON consolidado de entregas do projeto para o mês/ano."""
    try:
        with Session() as db:
            snap = OperacaoSnapshotService.get_snapshot(db, pipefy_id, mes, ano)
            return jsonify(snap or {})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/snapshot/links", methods=["PUT"])
@check_session
@check_access(["Account", "Gestor de Tráfego", "Cientista", "Desenvolvedor"])
def update_snapshot_links():
    """Salva links fixos (kpis, forecasting, relatorio_account, relatorio_gt) no snapshot."""
    data = request.json or {}
    email = session.get("email")
    pipefy_id = data.get("pipefy_id")
    mes = data.get("mes")
    ano = data.get("ano")
    tipo = data.get("tipo")
    link = data.get("link", "")

    valid_tipos = ["kpis", "forecasting", "relatorio_account", "relatorio_gt", "relatorio_mensal"]
    if not all([pipefy_id, mes, ano, tipo]) or tipo not in valid_tipos:
        return jsonify({"error": "Parâmetros inválidos"}), 400

    try:
        with Session() as db:
            OperacaoSnapshotService.update_section(
                db, pipefy_id, int(mes), int(ano),
                tipo, {"link": link},
            )
            db.commit()
        _sync_metrica_entregas_operacao(email, int(pipefy_id), int(mes), int(ano))
        return jsonify({"ok": True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[snapshot] links: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/otimizacao", methods=["POST"])
@check_session
@check_access(["Account", "Gestor de Tráfego", "Cientista", "Gerência", "Desenvolvedor"])
def save_otimizacao_api():
    """Salva otimização APENAS na tabela operacao.entregas.otimizacoes (append)."""
    data = request.json or {}
    email = session.get("email")
    pipefy_id = data.get("pipefy_id")
    d = dt.strptime(data.get("data", ""), "%Y-%m-%d") if data.get("data") else dt.now()
    mes, ano = d.month, d.year

    print(f"[otimizacao POST] email={email} projeto={pipefy_id} mes={mes} ano={ano}")

    otim_snap = {
        "canal": data.get("canal", ""),
        "data_da_otimizacao": data.get("data", ""),
        "oquesera_otimizado": data.get("tipo", ""),
        "detalhes_otimizacao": data.get("detalhes", ""),
        "criado_por": email,
    }

    ok = _operacao_save_section(pipefy_id, mes, ano, "otimizacoes", otim_snap, append=True)
    if not ok:
        return jsonify({"error": "Falha ao salvar na tabela operacao"}), 500

    _sync_metrica_entregas_operacao(email, pipefy_id, mes, ano)
    return jsonify({"status": "success"})

@app.route("/api/operacao/checkin", methods=["POST"])
@check_session
@check_access(["Account", "Cientista", "Gerência", "Desenvolvedor", "Gestor de Tráfego"])
def save_checkin():
    """Salva checkin APENAS na tabela operacao.entregas.checkin_semanal (append)."""
    data = request.json or {}
    email = session.get("email")
    pipefy_id = data.get("pipefy_id")
    # Permite check-in retroativo: deriva mes/ano da data informada (igual à otimização).
    d = dt.strptime(data.get("data", ""), "%Y-%m-%d") if data.get("data") else dt.now()
    mes, ano = d.month, d.year

    print(f"[checkin POST] email={email} projeto={pipefy_id} mes={mes} ano={ano}")

    checkin_snap = {
        "data": d.strftime("%Y-%m-%d"),
        "semana": data.get("semana_ano", ""),
        "stakeholder_participou": data.get("compareceu", False),
        "campanhas_ativas": data.get("campanhas_ativas", True),
        "gap_comunicacao": data.get("gap_comunicacao", False),
        "cliente_reclamou": data.get("cliente_reclamou", False),
        "observacoes": data.get("obs", ""),
        "links": [data["transcricao_url"]] if data.get("transcricao_url") else [],
        "criado_por": email,
    }

    ok = _operacao_save_section(pipefy_id, mes, ano, "checkin_semanal", checkin_snap, append=True)
    if not ok:
        return jsonify({"error": "Falha ao salvar na tabela operacao"}), 500

    _sync_metrica_entregas_operacao(email, pipefy_id, mes, ano)
    return jsonify({"status": "success"})


@app.route("/api/operacao/checkins/<int:pipefy_id>", methods=["GET"])
@check_session
@check_access(["Account", "Gestor de Tráfego", "Cientista", "Desenvolvedor"])
def get_checkins(pipefy_id):
    """Lista todos os checkins do projeto — lê da tabela operacao."""
    try:
        with Session() as db:
            rows = db.execute(text(
                "SELECT mes, ano, entregas FROM plataforma_geral.operacao "
                "WHERE id_projeto = :id ORDER BY ano DESC, mes DESC"
            ), {"id": str(pipefy_id)}).fetchall()

            result = []
            for r in rows:
                m, a = r.mes, r.ano
                ent = r.entregas if isinstance(r.entregas, dict) else (
                    json.loads(r.entregas) if r.entregas else {}
                )
                for i, c in enumerate(ent.get("checkin_semanal") or []):
                    result.append({
                        "id": f"{m}-{a}-{i}",
                        "mes": m,
                        "ano": a,
                        "original_index": i,
                        "semana": c.get("semana", ""),
                        "compareceu": c.get("stakeholder_participou", False),
                        "campanhas_ativas": c.get("campanhas_ativas", True),
                        "gap_comunicacao": c.get("gap_comunicacao", False),
                        "cliente_reclamou": c.get("cliente_reclamou", False),
                        "satisfeito": True,
                        "csat": None,
                        "obs": c.get("observacoes", ""),
                        "data": c.get("data", ""),
                        "transcricao_url": (c.get("links") or [None])[0] if c.get("links") else None,
                    })
            return jsonify(result)
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─── GET OTIMIZAÇÕES ─────────────────────────────────────────────────────────

@app.route("/api/operacao/otimizacoes/<int:pipefy_id>", methods=["GET"])
@check_session
@check_access(["Account", "Gestor de Tráfego", "Cientista", "Desenvolvedor"])
def get_otimizacoes(pipefy_id):
    """Lista todas as otimizações do projeto (todos os meses) — lê da tabela operacao."""
    try:
        with Session() as db:
            rows = db.execute(text(
                "SELECT mes, ano, entregas FROM plataforma_geral.operacao "
                "WHERE id_projeto = :id ORDER BY ano DESC, mes DESC"
            ), {"id": str(pipefy_id)}).fetchall()

            result = []
            for r in rows:
                m, a = r.mes, r.ano
                ent = r.entregas if isinstance(r.entregas, dict) else (
                    json.loads(r.entregas) if r.entregas else {}
                )
                for i, o in enumerate(ent.get("otimizacoes") or []):
                    result.append({
                        "id": f"{m}-{a}-{i}",
                        "mes": m,
                        "ano": a,
                        "original_index": i,
                        "tipo": o.get("oquesera_otimizado", ""),
                        "canal": o.get("canal", ""),
                        "data": o.get("data_da_otimizacao", ""),
                        "detalhes": o.get("detalhes_otimizacao", ""),
                        "criado_em": o.get("data_da_otimizacao", ""),
                    })
            return jsonify(result)
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─── LINKS ÚTEIS ─────────────────────────────────────────────────────────────

@app.route("/api/operacao/links/<int:pipefy_id>", methods=["GET"])
@check_session
@check_access(["Account", "Gestor de Tráfego", "Desenvolvedor"])
def get_links(pipefy_id):
    try:
        with Session() as db:
            links = db.query(OperacaoLinkUtil).filter_by(
                projeto_pipefy_id=pipefy_id
            ).order_by(OperacaoLinkUtil.created_at.desc()).all()
            return jsonify([{
                "id": lk.id,
                "titulo": lk.titulo,
                "url": lk.url,
                "descricao": lk.descricao,
                "icone": lk.icone or "fa-link",
                "criado_por": lk.criado_por
            } for lk in links])
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/links", methods=["POST"])
@check_session
@check_access(["Account", "Gestor de Tráfego", "Desenvolvedor"])
def save_link():
    data = request.json
    email = session.get("email")
    try:
        with Session() as db:
            if not data.get("titulo") or not data.get("url"):
                return jsonify({"error": "Título e URL são obrigatórios."}), 400
            lk = OperacaoLinkUtil(
                projeto_pipefy_id=data["pipefy_id"],
                titulo=data["titulo"],
                url=data["url"],
                descricao=data.get("descricao"),
                icone=data.get("icone", "fa-link"),
                criado_por=email,
                created_at=dt.now()
            )
            db.add(lk)
            db.commit()
            return jsonify({"status": "success", "id": lk.id})
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/links/<int:link_id>", methods=["DELETE"])
@check_session
@check_access(["Account", "Gestor de Tráfego", "Desenvolvedor"])
def delete_link(link_id):
    try:
        with Session() as db:
            lk = db.get(OperacaoLinkUtil, link_id)
            if lk:
                db.delete(lk)
                db.commit()
            return jsonify({"status": "success"})
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


# ─── NOVAS ROTAS DE DELEÇÃO OPERAÇÃO ──────────────────────────────────────────

@app.route("/api/operacao/checkin/<int:pipefy_id>/<int:mes>/<int:ano>/<int:index>", methods=["DELETE"])
@check_session
@check_access(["Account", "Gestor de Tráfego", "Cientista", "Desenvolvedor"])
def delete_checkin_api(pipefy_id, mes, ano, index):
    try:
        snap = _operacao_get_snapshot(pipefy_id, mes, ano)
        if not snap or "checkin_semanal" not in snap:
            return jsonify({"error": "Check-in não encontrado"}), 404
        
        lst = list(snap["checkin_semanal"])
        if index < 0 or index >= len(lst):
            return jsonify({"error": "Índice inválido"}), 400
        
        del lst[index]
        
        with engine.begin() as conn:
            snap["checkin_semanal"] = lst
            conn.execute(text(
                "UPDATE plataforma_geral.operacao SET entregas = CAST(:ent AS jsonb) "
                "WHERE id_projeto = :id AND mes = :mes AND ano = :ano"
            ), {"ent": json.dumps(snap, ensure_ascii=False), "id": str(pipefy_id), "mes": mes, "ano": ano})
            
        _sync_metrica_entregas_operacao(session.get("email"), pipefy_id, mes, ano)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/otimizacao/<int:pipefy_id>/<int:mes>/<int:ano>/<int:index>", methods=["DELETE"])
@check_session
@check_access(["Gestor de Tráfego", "Cientista", "Gerência", "Desenvolvedor"])
def delete_otimizacao_api(pipefy_id, mes, ano, index):
    try:
        snap = _operacao_get_snapshot(pipefy_id, mes, ano)
        if not snap or "otimizacoes" not in snap:
            return jsonify({"error": "Otimização não encontrada"}), 404
        
        lst = list(snap["otimizacoes"])
        if index < 0 or index >= len(lst):
            return jsonify({"error": "Índice inválido"}), 400
        
        del lst[index]
        
        with engine.begin() as conn:
            snap["otimizacoes"] = lst
            conn.execute(text(
                "UPDATE plataforma_geral.operacao SET entregas = CAST(:ent AS jsonb) "
                "WHERE id_projeto = :id AND mes = :mes AND ano = :ano"
            ), {"ent": json.dumps(snap, ensure_ascii=False), "id": str(pipefy_id), "mes": mes, "ano": ano})
            
        _sync_metrica_entregas_operacao(session.get("email"), pipefy_id, mes, ano)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/plano-midia/<int:pipefy_id>/<int:mes>/<int:ano>", methods=["DELETE"])
@check_session
@check_access(["Gestor de Tráfego", "Cientista", "Gerência", "Account", "Desenvolvedor"])
def delete_plano_midia_api(pipefy_id, mes, ano):
    try:
        snap = _operacao_get_snapshot(pipefy_id, mes, ano)
        if not snap:
            return jsonify({"error": "Plano não encontrado"}), 404
        
        with engine.begin() as conn:
            snap["plano_midia"] = {"budget_total": 0, "planos": []}
            conn.execute(text(
                "UPDATE plataforma_geral.operacao SET entregas = CAST(:ent AS jsonb) "
                "WHERE id_projeto = :id AND mes = :mes AND ano = :ano"
            ), {"ent": json.dumps(snap, ensure_ascii=False), "id": str(pipefy_id), "mes": mes, "ano": ano})
            
        _sync_metrica_entregas_operacao(session.get("email"), pipefy_id, mes, ano)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── GESTÃO DE PROJETOS (EDIÇÃO E VINCULAÇÃO) ────────────────────────────────

@app.route("/api/admin/investidores-ativos", methods=["GET"])
@check_session
@check_access(["Gerência"])
def get_investidores_ativos():
    """Retorna lista de investidores ativos para vinculação."""
    try:
        with Session() as db:
            investidores = db.query(Investidor).filter_by(ativo=True).order_by(Investidor.nome).all()
            return jsonify([{
                "email": inv.email,
                "nome": inv.nome
            } for inv in investidores])
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projetos/<int:pipefy_id>/vinculos", methods=["GET"])
@check_session
def get_projeto_vinculos(pipefy_id):
    """Retorna investidores vinculados a um projeto, com data_inicio resolvida e metadata."""
    try:
        with Session() as db:
            # Busca o projeto para pegar o metadata no campo extra
            projeto = db.query(Projeto).filter_by(pipefy_id=pipefy_id).first()
            
            investidores_metadata = {}
            if projeto and projeto.extra and isinstance(projeto.extra, dict):
                investidores_metadata = projeto.extra.get("investidores_metadata", {})

            vinculos = db.query(InvestidorProjeto).filter_by(pipefy_id_projeto=pipefy_id).all()

            # Pré-carrega dados dos investidores (nome, função, posição, foto)
            todos_emails = list({v.email_investidor for v in vinculos})
            investidores_info = {}
            if todos_emails:
                invs = db.query(Investidor).filter(Investidor.email.in_(todos_emails)).all()
                for inv in invs:
                    investidores_info[inv.email] = {
                        "nome": inv.nome,
                        "funcao": inv.funcao,
                        "posicao": inv.posicao,
                        "profile_picture": (
                            f"/static/images/profile_pictures/{inv.profile_picture}"
                            if inv.profile_picture else None
                        ),
                    }

            # Pré-carrega MetricaMensal mais recente de cada email para buscar data_inicio no historico
            emails = list({v.email_investidor for v in vinculos if not v.created_at})
            historico_map = {}  # email → data_inicio (str ISO)
            if emails:
                from sqlalchemy import func
                # Pega o registro mais recente (maior ano/mes) de cada email
                sub = (
                    db.query(
                        MetricaMensal.email_investidor,
                        func.max(MetricaMensal.ano * 100 + MetricaMensal.mes).label("ym")
                    )
                    .filter(MetricaMensal.email_investidor.in_(emails))
                    .group_by(MetricaMensal.email_investidor)
                    .subquery()
                )
                metricas = (
                    db.query(MetricaMensal)
                    .join(sub, (MetricaMensal.email_investidor == sub.c.email_investidor) &
                               ((MetricaMensal.ano * 100 + MetricaMensal.mes) == sub.c.ym))
                    .all()
                )
                for m in metricas:
                    if not m.historico_projetos:
                        continue
                    for item in m.historico_projetos:
                        if str(item.get("projeto_id")) == str(pipefy_id) and item.get("data_inicio"):
                            historico_map[m.email_investidor] = item["data_inicio"]
                            break

            result = []
            for v in vinculos:
                if v.created_at:
                    data_inicio = v.created_at.isoformat()
                else:
                    data_inicio = historico_map.get(v.email_investidor)
                
                # Metadata do cientista
                meta = investidores_metadata.get(v.email_investidor, {})
                info = investidores_info.get(v.email_investidor, {})

                result.append({
                    "id": v.id,
                    "email": v.email_investidor,
                    "nome": info.get("nome"),
                    "funcao": info.get("funcao"),
                    "posicao": info.get("posicao"),
                    "profile_picture": info.get("profile_picture"),
                    "cientista": v.cientista,
                    "active": v.active,
                    "fee_contribuicao": float(v.fee_contribuicao or 0),
                    "data_inicio": data_inicio,
                    "data_fim": v.inactivated_at.isoformat() if v.inactivated_at else None,
                    "cientista_entrada": meta.get("cientista_entrada"),
                    "cientista_saida": meta.get("cientista_saida")
                })
            return jsonify(result)
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projetos/vincular", methods=["POST"])
@check_session
@check_access(["Gerência", "Sócio", "Coordenador"])
def vincular_investidor():
    """Vincula um investidor a um projeto."""
    data = request.json
    email_investidor = data.get("email_investidor")
    pipefy_id = data.get("pipefy_id_projeto")
    cientista = data.get("cientista", False)

    user_posicao = session.get("posicao")
    user_squad = session.get("squad")

    if user_posicao == "Coordenador":
        if not user_squad:
            return jsonify({"error": "Coordenador sem Squad atribuída."}), 403
        
        # Valida se o projeto pertence à squad do coordenador
        try:
            with Session() as db:
                projeto = db.query(Projeto).filter_by(pipefy_id=str(pipefy_id)).first()
                
                if not projeto or projeto.squad_atribuida != user_squad:
                    return jsonify({"error": "Acesso restrito à sua Squad."}), 403
        except SQLAlchemyError:
            pass # Continua para a lógica principal que lidará com erros de banco
    
    if not email_investidor or not pipefy_id:
        return jsonify({"error": "E-mail e ID do projeto são obrigatórios."}), 400

    try:
        with Session() as db:
            # Busca dados do projeto para denormalização na tabela unificada
            projeto = db.query(Projeto).filter_by(pipefy_id=pipefy_id).first()
            
            if not projeto:
                return jsonify({"error": "Projeto não encontrado."}), 404

            # Verifica se já existe vínculo
            vinculo = db.query(InvestidorProjeto).filter_by(
                email_investidor=email_investidor,
                pipefy_id_projeto=pipefy_id
            ).first()

            if vinculo:
                vinculo.active = True
                vinculo.cientista = cientista
                vinculo.nome_projeto = projeto.nome
                vinculo.fee_projeto = projeto.fee
            else:
                max_id = db.query(InvestidorProjeto.id).order_by(InvestidorProjeto.id.desc()).first()
                new_id = (max_id[0] + 1) if max_id else 1
                
                vinculo = InvestidorProjeto(
                    id=new_id,
                    email_investidor=email_investidor,
                    pipefy_id_projeto=pipefy_id,
                    active=True,
                    cientista=cientista,
                    nome_projeto=projeto.nome,
                    fee_projeto=projeto.fee,
                    created_at=dt.now().date()
                )
                db.add(vinculo)
            
            db.commit()
            return jsonify({"status": "success", "message": "Investidor vinculado com sucesso."})
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projetos/<int:pipefy_id>", methods=["PUT"])
@check_session
@check_access(["Gerência", "Sócio", "Coordenador"])
def update_projeto_local(pipefy_id):
    """Atualiza dados do projeto e sincroniza vínculos."""
    data = request.json
    user_posicao = session.get("posicao")
    user_squad = session.get("squad")

    try:
        from decimal import Decimal
        with Session() as db:
            projeto = db.query(Projeto).filter_by(pipefy_id=pipefy_id).first()
            is_onetime = (projeto.status == 'Onetime') if projeto else False
            is_inativo = (projeto.status == 'Inativo') if projeto else False
            
            if not projeto:
                return jsonify({"error": "Projeto não encontrado."}), 404

            # Validação de Squad para Coordenador
            if user_posicao == "Coordenador":
                if not user_squad or projeto.squad_atribuida != user_squad:
                    return jsonify({"error": "Acesso restrito à sua Squad."}), 403

            # Rastreamento de alterações para o histórico
            changes = {}
            fields_to_track = {
                "nome": "Nome",
                "pipefy_id": "Pipefy ID",
                "documento": "Documento",
                "fee": "Fee",
                "moeda": "Moeda",
                "squad_atribuida": "Squad",
                "produto_contratado": "Produto",
                "cohort": "Cohort",
                "meta_account_id": "Meta Account ID",
                "google_account_id": "Google Account ID",
                "fase_do_pipefy": "Fase Pipefy",
                "url_webhook_gchat": "Webhook GChat",
                "ekyte_workspace": "Ekyte Workspace",
                "step": "Fase",
                "informacoes_gerais": "Informações Gerais",
                "orcamento_midia_meta": "Orçamento Meta",
                "orcamento_midia_google": "Orçamento Google"
            }

            for field, label in fields_to_track.items():
                if field in data:
                    new_val = data[field]
                    if field == "fee": 
                        new_val = int(new_val)
                    
                    old_val = getattr(projeto, field)
                    if str(old_val) != str(new_val):
                        changes[field] = {
                            "antes": str(old_val) if old_val is not None else "",
                            "depois": str(new_val)
                        }

            # Atualiza campos básicos do projeto
            if "nome" in data: projeto.nome = data["nome"]
            if "documento" in data: projeto.documento = data["documento"]
            if "fee" in data: projeto.fee = int(float(data["fee"] or 0))
            if "moeda" in data: projeto.moeda = data["moeda"]
            if "squad_atribuida" in data: projeto.squad_atribuida = data["squad_atribuida"]
            if "produto_contratado" in data: projeto.produto_contratado = data["produto_contratado"]
            if "cohort" in data: projeto.cohort = data["cohort"]
            if "meta_account_id" in data: projeto.meta_account_id = data["meta_account_id"]
            if "google_account_id" in data: projeto.google_account_id = data["google_account_id"]
            if "fase_do_pipefy" in data: projeto.fase_do_pipefy = data["fase_do_pipefy"]
            if "url_webhook_gchat" in data: projeto.url_webhook_gchat = data["url_webhook_gchat"]
            if "step" in data: projeto.step = data["step"]
            if "informacoes_gerais" in data: projeto.informacoes_gerais = data["informacoes_gerais"]
            if "ekyte_workspace" in data: projeto.ekyte_workspace = data["ekyte_workspace"]
            
            # Orçamentos: Resetar se for inativo, senão atualizar
            if is_inativo or data.get("tipo_projeto") == "inativo":
                projeto.orcamento_midia_meta = 0
                projeto.orcamento_midia_google = 0
            else:
                if "orcamento_midia_meta" in data:
                    projeto.orcamento_midia_meta = int(float(data["orcamento_midia_meta"] or 0))
                if "orcamento_midia_google" in data:
                    projeto.orcamento_midia_google = int(float(data["orcamento_midia_google"] or 0))

            # Datas: Seguir o padrão 2900-01-01 se vazio (conforme n8n)
            from datetime import date as date_type
            data_placeholder = date_type(2900, 1, 1)

            if "data_de_inicio" in data:
                val = data["data_de_inicio"]
                try:
                    projeto.data_de_inicio = date_type.fromisoformat(val) if val else data_placeholder
                except ValueError:
                    projeto.data_de_inicio = data_placeholder

            if "data_fim" in data:
                val = data["data_fim"]
                try:
                    projeto.data_fim = date_type.fromisoformat(val) if val else data_placeholder
                except ValueError:
                    projeto.data_fim = data_placeholder
            
            # Atualiza notas
            if "notas" in data:
                projeto.notas = data["notas"]

            # Atualiza flag de contrato variável (persistida no campo JSONB extra)
            if "contrato_variavel" in data:
                contrato_var_val = bool(data.get("contrato_variavel"))
                # Rastrear mudança no histórico
                old_contrato_var = bool((projeto.extra or {}).get("contrato_variavel", False))
                if old_contrato_var != contrato_var_val:
                    changes["contrato_variavel"] = {
                        "antes": "Sim" if old_contrato_var else "Não",
                        "depois": "Sim" if contrato_var_val else "Não"
                    }

            # Registra no histórico se houver mudanças
            if changes:
                historico_entry = {
                    "data": dt.now().isoformat(),
                    "usuario": session.get("email", "Sistema"),
                    "alteracoes": changes
                }
                
                if projeto.extra is None:
                    projeto.extra = {"historico": []}
                elif "historico" not in projeto.extra:
                    # Garantir que não sobrescrevemos outros dados em extra se existirem
                    new_extra = dict(projeto.extra)
                    new_extra["historico"] = []
                    projeto.extra = new_extra
                
                # SQLAlchemy JSONB mutation tracking can be tricky, 
                # so we re-assign to ensure it detects the change
                new_extra = dict(projeto.extra)
                new_extra["historico"].insert(0, historico_entry)
                projeto.extra = new_extra

            # Sincroniza vínculos (denormalização e reconciliação)
            incoming_investidores = data.get("investidores", [])
            current_emails = [inv.get("email") for inv in incoming_investidores if inv.get("email")]
            
            # Metadata para cientista (será salvo no projeto.extra)
            investidores_metadata = {}
            if projeto.extra and isinstance(projeto.extra, dict):
                investidores_metadata = dict(projeto.extra.get("investidores_metadata", {}))

            # 1. Remove vínculos que não estão na lista recebida
            db.query(InvestidorProjeto).filter(
                InvestidorProjeto.pipefy_id_projeto == pipefy_id,
                ~InvestidorProjeto.email_investidor.in_(current_emails)
            ).delete(synchronize_session=False)

            # 2. Atualiza ou Cria novos vínculos
            for inv_data in incoming_investidores:
                email = inv_data.get("email")
                if not email: continue
                
                v = db.query(InvestidorProjeto).filter_by(
                    pipefy_id_projeto=pipefy_id, 
                    email_investidor=email
                ).first()
                
                cientista = inv_data.get("cientista", False)
                active = inv_data.get("active", True)
                
                # Parse de datas
                from datetime import date as date_type
                
                def parse_date(d_str):
                    if not d_str: return None
                    try:
                        return date_type.fromisoformat(d_str.split('T')[0])
                    except ValueError:
                        return None

                data_inicio_obj = parse_date(inv_data.get("data_inicio"))
                data_fim_obj = parse_date(inv_data.get("data_fim"))
                
                # Metadata do cientista
                investidores_metadata[email] = {
                    "cientista_entrada": inv_data.get("cientista_entrada"),
                    "cientista_saida": inv_data.get("cientista_saida")
                }

                if v:
                    # Atualiza existente
                    v.nome_projeto = data.get("nome", v.nome_projeto)
                    v.fee_projeto = Decimal(str(data.get("fee", v.fee_projeto) or 0))
                    v.cientista = cientista
                    v.active = active
                    v.inactivated_at = data_fim_obj
                    if data_inicio_obj:
                        v.created_at = data_inicio_obj
                        # Propaga a nova data_inicio para historico_projetos em todos os meses
                        metricas = db.query(MetricaMensal).filter_by(email_investidor=email).all()
                        for metrica in metricas:
                            if not metrica.historico_projetos:
                                continue
                            novo_hist = []
                            atualizado = False
                            for item in metrica.historico_projetos:
                                if str(item.get("projeto_id")) == str(pipefy_id):
                                    item = dict(item)
                                    item["data_inicio"] = data_inicio_obj.isoformat()
                                    item["data_fim"] = data_fim_obj.isoformat() if data_fim_obj else None
                                    item["active"] = active
                                    item["cientista"] = cientista
                                    
                                    # Datas de cientista do metadata recém-coletado
                                    inv_m = investidores_metadata.get(email, {})
                                    c_ent = inv_m.get("cientista_entrada")
                                    c_sai = inv_m.get("cientista_saida")
                                    item["cientista_entrada"] = c_ent.split('T')[0] if c_ent else None
                                    item["cientista_saida"] = c_sai.split('T')[0] if c_sai else None
                                    
                                    atualizado = True
                                novo_hist.append(item)
                            if atualizado:
                                metrica.historico_projetos = novo_hist
                                flag_modified(metrica, "historico_projetos")
                else:
                    # Cria novo
                    created = data_inicio_obj if data_inicio_obj else dt.now().date()
                    novo_v = InvestidorProjeto(
                        pipefy_id_projeto=pipefy_id,
                        email_investidor=email,
                        nome_projeto=data.get("nome", projeto.nome),
                        fee_projeto=Decimal(str(data.get("fee", projeto.fee) or 0)),
                        cientista=cientista,
                        active=active,
                        created_at=created,
                        inactivated_at=data_fim_obj
                    )
                    db.add(novo_v)

            # Salva o metadata no extra do projeto (inclui contrato_variavel e investidores_metadata)
            if not projeto.extra:
                projeto.extra = {}
            new_extra = dict(projeto.extra)
            new_extra["investidores_metadata"] = investidores_metadata
            # Persiste a flag de contrato variável no extra
            if "contrato_variavel" in data:
                new_extra["contrato_variavel"] = bool(data.get("contrato_variavel"))
            projeto.extra = new_extra
            flag_modified(projeto, "extra")

            db.commit()
            
            # Sincroniza a remuneração imediatamente para refletir as mudanças no histórico proporcional
            try:
                ProjetoParticipacaoService.sincronizar_remuneracao(dt.now().month, dt.now().year)
            except Exception as e:
                print(f"Erro na sincronização pós-update: {e}")

            # Aplica valores de faturamento variável sobre o MRR calculado (serviço isolado)
            try:
                from services.faturamento_variavel import aplicar_faturamento_variavel
                aplicar_faturamento_variavel(dt.now().month, dt.now().year)
            except Exception as e:
                print(f"Erro ao aplicar faturamento variável pós-update: {e}")

            return jsonify({"status": "success", "message": "Projeto e vínculos sincronizados com sucesso."})

    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projetos/listar", methods=["GET"])
@check_session
def api_listar_projetos():
    """Lista projetos do banco local para atualização dinâmica da UI."""
    squad = session.get("squad", "")
    email = session.get("email", "")
    
    # Busca dados locais
    ativos = _buscar_projetos_db(Projeto, email, squad, status='Ativo')
    onetime = _buscar_projetos_db(Projeto, email, squad, status='Onetime')
    inativos = _buscar_projetos_db(Projeto, email, squad, status='Inativo')
    
    # Formata para ser compatível com o que atualizarCards espera (baseado no formato n8n legado se necessário, 
    # mas aqui adaptamos para simplificar)
    return jsonify({
        "ativos": [{"projetos": p} for p in ativos],
        "onetime": [{"projetos": p} for p in onetime],
        "inativos": [{"projetos": p} for p in inativos]
    })


# ─── FATURAMENTO VARIÁVEL ──────────────────────────────────────────────────────
# Rotas isoladas para CRUD do faturamento variável por projeto/mês/ano.
# Não alteram modelos, serviços existentes nem schema do banco.

@app.route("/api/projetos/<int:pipefy_id>/faturamento-variavel", methods=["GET"])
@check_session
def get_faturamento_variavel(pipefy_id):
    """Retorna registros de faturamento variável de um projeto. Aceita ?mes=&ano= para filtrar."""
    try:
        from services.faturamento_variavel import get_registros_por_projeto
        mes = request.args.get("mes", type=int)
        ano = request.args.get("ano", type=int)
        registros = get_registros_por_projeto(pipefy_id, mes=mes, ano=ano)
        return jsonify({"registros": registros})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projetos/<int:pipefy_id>/faturamento-variavel", methods=["POST"])
@check_session
def post_faturamento_variavel(pipefy_id):
    """Cria ou atualiza o registro de faturamento variável para um mês/ano.
    Acesso restrito: somente usuários com permissão de edição de projetos."""
    nivel = session.get("nivel_acesso", "Usuário")
    if nivel == "Usuário":
        return jsonify({"error": "Sem permissão para criar registros de faturamento variável."}), 403

    data = request.json or {}
    mes = data.get("mes")
    ano = data.get("ano")
    faturamento_cliente = data.get("faturamento_cliente")
    percentual = data.get("percentual")

    if not all([mes, ano, faturamento_cliente is not None, percentual is not None]):
        return jsonify({"error": "Campos obrigatórios: mes, ano, faturamento_cliente, percentual"}), 400

    try:
        from services.faturamento_variavel import salvar_registro, aplicar_faturamento_variavel
        ok, msg = salvar_registro(
            pipefy_id=pipefy_id,
            mes=int(mes),
            ano=int(ano),
            faturamento_cliente=float(faturamento_cliente),
            percentual=float(percentual),
            usuario_email=session.get("email", "sistema"),
            registro_id=data.get("id")
        )
        if not ok:
            return jsonify({"error": msg}), 500

        # Re-aplica o faturamento variável ao MRR do mês atual
        try:
            aplicar_faturamento_variavel(int(mes), int(ano))
        except Exception as e:
            print(f"[fat_var] Erro ao aplicar MRR pós-save: {e}")

        return jsonify({"status": "success", "message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projetos/<int:pipefy_id>/faturamento-variavel/<int:mes>/<int:ano>", methods=["PUT"])
@check_session
def put_faturamento_variavel(pipefy_id, mes, ano):
    """Atualiza o registro de faturamento variável de um mês/ano específico.
    Delega ao POST (upsert idempotente)."""
    nivel = session.get("nivel_acesso", "Usuário")
    if nivel == "Usuário":
        return jsonify({"error": "Sem permissão para editar registros de faturamento variável."}), 403

    data = request.json or {}
    data["mes"] = mes
    data["ano"] = ano
    # Reutiliza lógica do POST
    try:
        from services.faturamento_variavel import salvar_registro, aplicar_faturamento_variavel
        faturamento_cliente = data.get("faturamento_cliente")
        percentual = data.get("percentual")
        if faturamento_cliente is None or percentual is None:
            return jsonify({"error": "Campos obrigatórios: faturamento_cliente, percentual"}), 400

        ok, msg = salvar_registro(
            pipefy_id=pipefy_id,
            mes=int(mes),
            ano=int(ano),
            faturamento_cliente=float(faturamento_cliente),
            percentual=float(percentual),
            usuario_email=session.get("email", "sistema"),
            registro_id=data.get("id")
        )
        if not ok:
            return jsonify({"error": msg}), 500

        try:
            aplicar_faturamento_variavel(int(mes), int(ano))
        except Exception as e:
            print(f"[fat_var] Erro ao aplicar MRR pós-edit: {e}")

        return jsonify({"status": "success", "message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projetos/<int:pipefy_id>/faturamento-variavel/<int:mes>/<int:ano>", methods=["DELETE"])
@check_session
def delete_faturamento_variavel(pipefy_id, mes, ano):
    """Remove o registro de faturamento variável de um mês/ano específico."""
    nivel = session.get("nivel_acesso", "Usuário")
    if nivel == "Usuário":
        return jsonify({"error": "Sem permissão para remover registros de faturamento variável."}), 403

    try:
        from services.faturamento_variavel import deletar_registro, aplicar_faturamento_variavel
        registro_id = request.args.get("id")
        ok, msg = deletar_registro(pipefy_id=pipefy_id, mes=int(mes), ano=int(ano), registro_id=registro_id)
        if not ok:
            return jsonify({"error": msg}), 404

        # Recalcula apenas o impacto do faturamento variável (rápido)
        try:
            aplicar_faturamento_variavel(int(mes), int(ano))
        except Exception as e:
            print(f"[fat_var] Erro ao sincronizar MRR pós-delete: {e}")

        return jsonify({"status": "success", "message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ─── KANBAN INTEGRADO ─────────────────────────────────────────────────────────

@app.route("/kanban")
@check_session
def view_kanban():
    """Renderiza a dashboard de Kanban."""
    return render_template("kanban.html", user_name=session.get("nome"))

@app.route("/api/kanban/config", methods=["GET"])
@check_session
def api_kanban_config():
    """Retorna a configuração de um board Kanban."""
    slug = request.args.get("slug", "fluxo-projetos")
    with Session() as db:
        service = KanbanService(db)
        config = service.get_board_config(slug)
        return jsonify(config)

@app.route("/api/kanban/config", methods=["POST"])
@check_session
def api_kanban_save_config():
    """Salva a configuração de um board."""
    data = request.json or {}
    slug = data.get("_slug", "fluxo-projetos")
    configuracao = data
    configuracao.pop("_slug", None)
    
    if not configuracao:
        return jsonify({"error": "Configuração é obrigatória."}), 400
        
    with Session() as db:
        service = KanbanService(db)
        try:
            service.update_config(slug, configuracao)
            return jsonify({"status": "success"})
        except Exception as e:
            import traceback; traceback.print_exc()
            return jsonify({"error": str(e)}), 500

@app.route("/api/kanban/cards", methods=["GET"])
@check_session
def api_kanban_cards():
    """Lista os cards (projetos) para o Kanban."""
    slug = request.args.get("slug", "fluxo-projetos")
    with Session() as db:
        service = KanbanService(db)
        cards = service.list_cards(slug)
        
        # Otimização: buscar todo o histórico de uma vez para popular os badges no front
        from collections import defaultdict
        hist_map = defaultdict(list)
        historicos = db.query(KanbanHistorico).order_by(KanbanHistorico.data_evento.desc()).all()
        for h in historicos:
            hist_map[h.projeto_id].append({
                "id": h.id,
                "fase_entrada": h.snapshot.get("fase_concluida") or h.snapshot.get("fase") or h.snapshot.get("fase_entrada"),
                "fase_anterior": h.snapshot.get("fase_anterior") or h.snapshot.get("fase_concluida") if h.snapshot.get("evento") == "movimentacao" else None,
                "fase_nova": h.snapshot.get("fase_nova") or h.snapshot.get("fase") or h.snapshot.get("fase_entrada"),
                "dados": {
                    **(h.snapshot.get("snapshot_completo") or {}),
                    **(h.snapshot.get("dados_transicao") or {}),
                    **(h.snapshot.get("dados") or {})
                },
                "labels": h.snapshot.get("_labels") or {},
                "snapshot": h.snapshot,
                "evento": h.snapshot.get("evento"),
                "usuario": h.usuario_email,
                "timestamp": h.data_evento.isoformat()
            })
            
        for card in cards:
            card_id = card.get("card_id")
            if card_id in hist_map:
                card["historico"] = hist_map[card_id]
            else:
                card["historico"] = []
                
        return jsonify(cards)

@app.route("/api/kanban/cards/<int:card_id>", methods=["GET"])
@check_session
def api_kanban_get_card(card_id):
    """Retorna detalhes e histórico de um card."""
    with Session() as db:
        service = KanbanService(db)
        card_details = service.get_card(card_id)
        if not card_details:
            return jsonify({"error": "Projeto não encontrado."}), 404
        
        historico = db.query(KanbanHistorico).filter_by(projeto_id=card_id).order_by(KanbanHistorico.data_evento.desc()).all()
        
        card_details["historico"] = [
            {
                "id": h.id,
                "fase_entrada": h.snapshot.get("fase_concluida") or h.snapshot.get("fase") or h.snapshot.get("fase_entrada"),
                "fase_anterior": h.snapshot.get("fase_anterior") or h.snapshot.get("fase_concluida") if h.snapshot.get("evento") == "movimentacao" else None,
                "fase_nova": h.snapshot.get("fase_nova") or h.snapshot.get("fase") or h.snapshot.get("fase_entrada"),
                "dados": {
                    **(h.snapshot.get("snapshot_completo") or {}),
                    **(h.snapshot.get("dados_transicao") or {}),
                    **(h.snapshot.get("dados") or {})
                },
                "labels": h.snapshot.get("_labels") or {},
                "snapshot": h.snapshot,
                "evento": h.snapshot.get("evento"),
                "usuario": h.usuario_email,
                "timestamp": h.data_evento.isoformat()
            } for h in historico
        ]
        return jsonify(card_details)

@app.route("/api/kanban/cards/<int:card_id>/update", methods=["POST"])
@check_session
def api_kanban_update_card(card_id):
    """Atualiza dados de um card sem mover de fase."""
    if not session.get("pode_editar_kanban"):
        return jsonify({"error": "Você não tem permissão para editar o Kanban."}), 403
        
    data = request.json or {}
    dados = data.get("dados", {})
    with Session() as db:
        service = KanbanService(db)
        try:
            nome = data.get("nome")
            service.update_card(card_id, nome, dados, session.get('email', 'Sistema'))
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route("/api/kanban/history/<int:history_id>/update", methods=["POST"])
@check_session
def api_kanban_update_history(history_id):
    """Atualiza dados registrados em um histórico de fase anterior."""
    if not session.get("pode_editar_kanban"):
        return jsonify({"error": "Você não tem permissão para editar o Kanban."}), 403

    data = request.json or {}
    novos_dados = data.get("dados", {})
    
    with Session() as db:
        try:
            h = db.query(KanbanHistorico).filter_by(id=history_id).first()
            if not h:
                return jsonify({"error": "Registro de histórico não encontrado."}), 404
            
            projeto = db.query(Projeto).filter_by(pipefy_id=h.projeto_id).first()
            if not projeto:
                return jsonify({"error": "Projeto associado ao histórico não encontrado."}), 404

            service = KanbanService(db)
            config = service.get_board_config()
            
            snapshot = dict(h.snapshot)
            
            # Identificar dados antigos do snapshot
            old_dados = snapshot.get("dados") or snapshot.get("dados_transicao") or snapshot.get("snapshot_completo") or {}
            
            # Chaves de campo para obter os labels amigáveis
            labels = {}
            for fase in config.get('fases', []):
                for campo in fase.get('campos', []):
                    labels[campo['id']] = campo['label']

            changes = {}
            
            # Atualizar os dados do snapshot
            snapshot_dados = snapshot.get("dados")
            if snapshot_dados is None:
                snapshot["dados"] = {}
                snapshot_dados = snapshot["dados"]
            else:
                snapshot["dados"] = dict(snapshot_dados)
                snapshot_dados = snapshot["dados"]
            
            # Também atualizar snapshot_completo se existir
            snapshot_completo = snapshot.get("snapshot_completo")
            if snapshot_completo is not None:
                snapshot["snapshot_completo"] = dict(snapshot_completo)
                snapshot_completo = snapshot["snapshot_completo"]

            for k, v in novos_dados.items():
                val_antigo = old_dados.get(k)
                if val_antigo != v:
                    label_campo = labels.get(k, k)
                    changes[label_campo] = {
                        "antes": val_antigo if val_antigo is not None else "",
                        "depois": v
                    }
                    snapshot_dados[k] = v
                    if snapshot_completo is not None:
                        snapshot_completo[k] = v
            
            if not changes:
                return jsonify({"status": "success", "message": "Nenhuma alteração detectada."})
            
            # Guardar histórico de edições neste snapshot para rastreabilidade
            edicoes = snapshot.get("edicoes", [])
            edicoes.append({
                "usuario": session.get("email", "Sistema"),
                "data": dt.now().isoformat(),
                "alteracoes": changes
            })
            snapshot["edicoes"] = edicoes
            h.snapshot = snapshot
            flag_modified(h, "snapshot")
            
            # Propagar alterações para o card do projeto e suas colunas
            projeto_dados = dict(projeto.kanban_dados) if projeto.kanban_dados else {}
            for k, v in novos_dados.items():
                projeto_dados[k] = v
            
            projeto.kanban_dados = projeto_dados
            flag_modified(projeto, "kanban_dados")
            
            service._apply_column_mappings(projeto, config, projeto_dados)
            
            db.commit()
            return jsonify({"status": "success", "message": "Histórico e projeto atualizados com sucesso."})
        except Exception as e:
            db.rollback()
            return jsonify({"error": str(e)}), 500

@app.route("/api/kanban/move", methods=["POST"])
@check_session
def api_kanban_move():
    """Processa a movimentação de um card."""
    if not session.get("pode_editar_kanban"):
        return jsonify({"error": "Você não tem permissão para editar o Kanban."}), 403

    data = request.json or {}
    card_id = data.get("card_id")
    nova_fase_id = data.get("nova_fase_id")
    dados_fase = data.get("dados", {})
    usuario_email = session.get("email")

    if not card_id or not nova_fase_id:
        return jsonify({"error": "Parâmetros card_id e nova_fase_id são obrigatórios."}), 400

    with Session() as db:
        service = KanbanService(db)
        try:
            projeto = db.query(Projeto).filter_by(pipefy_id=int(card_id)).first()
            old_phase_name = projeto.fase_do_pipefy if projeto else ""
            config = service.get_board_config()
            old_phase = next((f for f in config.get("fases", []) if f["nome"] == old_phase_name), {})
            new_phase = next((f for f in config.get("fases", []) if f["id"] == nova_fase_id), {})

            service.move_card(int(card_id), nova_fase_id, dados_fase, usuario_email)

            project_date = projeto.data_de_inicio.isoformat() if projeto and projeto.data_de_inicio else None
            _disparar_automacoes_card_movido(
                int(card_id), projeto.nome if projeto else "",
                old_phase.get("id", ""), old_phase_name,
                new_phase.get("id", ""), new_phase.get("nome", ""),
                int(card_id), projeto.nome if projeto else "", project_date
            )

            return jsonify({"status": "success"})
        except PhaseTransitionError as e:
            return jsonify({"error": str(e)}), 422
        except Exception as e:
            import traceback; traceback.print_exc()
            return jsonify({"error": str(e)}), 500

@app.route("/api/kanban/cards", methods=["POST"])
@check_session
def api_kanban_create_card():
    """Cria um novo card (projeto)."""
    if not session.get("pode_editar_kanban"):
        return jsonify({"error": "Você não tem permissão para editar o Kanban."}), 403

    data = request.json or {}
    dados_iniciais = data.get("dados", {})
    usuario_email = session.get("email")

    with Session() as db:
        service = KanbanService(db)
        try:
            nome = data.get("nome", "Novo Projeto")
            projeto = service.create_card("fluxo-projetos", nome, dados_iniciais, usuario_email)
            config = service.get_board_config("fluxo-projetos")
            fases = config.get("fases", [])
            primeira_fase = fases[0] if fases else {"id": "", "nome": ""}
            project_date = projeto.data_de_inicio.isoformat() if projeto.data_de_inicio else None
            _disparar_automacoes_card_criado(
                projeto.pipefy_id, projeto.nome,
                primeira_fase["id"], primeira_fase["nome"],
                projeto.pipefy_id, projeto.nome, project_date
            )
            return jsonify({"status": "success", "card_id": projeto.pipefy_id})
        except Exception as e:
            import traceback; traceback.print_exc()
            return jsonify({"error": str(e)}), 500


@app.route("/api/kanban/cards/clone-from-history", methods=["POST"])
@check_session
def api_kanban_clone_from_history():
    """Clona um card a partir de um snapshot do histórico."""
    if not session.get("pode_editar_kanban"):
        return jsonify({"error": "Você não tem permissão para editar o Kanban."}), 403

    data = request.json or {}
    history_id = data.get("history_id")
    nome = data.get("nome", "Card Clonado")
    board_slug = data.get("board_slug", "fluxo-projetos")
    usuario_email = session.get("email")

    if not history_id:
        return jsonify({"error": "history_id é obrigatório."}), 400

    with Session() as db:
        service = KanbanService(db)
        try:
            projeto = service.clone_card_from_history(history_id, nome, usuario_email, slug=board_slug)
            return jsonify({"status": "success", "card_id": projeto.pipefy_id})
        except Exception as e:
            import traceback; traceback.print_exc()
            return jsonify({"error": str(e)}), 500


@app.route("/api/kanban/boards", methods=["GET"])
@check_session
def api_kanban_boards():
    """Lista todos os boards Kanban."""
    with Session() as db:
        service = KanbanService(db)
        boards = service.list_boards()
        return jsonify(boards)


@app.route("/api/kanban/boards", methods=["POST"])
@check_session
def api_kanban_create_board():
    """Cria um novo board Kanban."""
    if not session.get("pode_editar_kanban"):
        return jsonify({"error": "Você não tem permissão para editar o Kanban."}), 403

    data = request.json or {}
    slug = data.get("slug", "").strip().lower().replace(" ", "-")
    nome = data.get("nome", slug)

    if not slug:
        return jsonify({"error": "Slug é obrigatório."}), 400

    with Session() as db:
        service = KanbanService(db)
        try:
            config = service.create_board(slug, nome)
            return jsonify({"status": "success", "slug": slug, "config": config})
        except ValueError as e:
            return jsonify({"error": str(e)}), 409
        except Exception as e:
            import traceback; traceback.print_exc()
            return jsonify({"error": str(e)}), 500


@app.route("/api/kanban/cards/migrate-board", methods=["POST"])
@check_session
def api_kanban_migrate_card_board():
    """Transfere um card para outro board."""
    if not session.get("pode_editar_kanban"):
        return jsonify({"error": "Você não tem permissão para editar o Kanban."}), 403

    data = request.json or {}
    card_id = data.get("card_id")
    target_slug = data.get("target_slug")
    usuario_email = session.get("email")

    if not card_id or not target_slug:
        return jsonify({"error": "card_id e target_slug são obrigatórios."}), 400

    with Session() as db:
        service = KanbanService(db)
        try:
            projeto = service.migrate_card_to_board(card_id, target_slug, usuario_email)
            return jsonify({"status": "success", "card_id": projeto.pipefy_id, "nova_fase": projeto.fase_do_pipefy})
        except Exception as e:
            import traceback; traceback.print_exc()
            return jsonify({"error": str(e)}), 500


# ─── AUTOMAÇÕES (Webhooks) ──────────────────────────────────────────────────

@app.route("/automacoes")
@check_session
def view_automacoes():
    """Renderiza a página de automações."""
    return render_template("automacoes.html", user_name=session.get("nome"))


@app.route("/api/automacoes", methods=["GET"])
@check_session
def api_automacoes_list():
    """Lista todas as automações."""
    with Session() as db:
        service = AutomacaoService(db)
        return jsonify(service.list_automacoes())


@app.route("/api/automacoes", methods=["POST"])
@check_session
def api_automacoes_create():
    """Cria uma nova automação."""
    data = request.json or {}
    if not data.get("nome"):
        return jsonify({"error": "Nome é obrigatório."}), 400
    if not data.get("trigger_type"):
        return jsonify({"error": "Tipo de gatilho é obrigatório."}), 400
    if not data.get("action_config", {}).get("url"):
        return jsonify({"error": "URL do webhook é obrigatória."}), 400

    with Session() as db:
        service = AutomacaoService(db)
        try:
            a = service.create_automacao(data)
            return jsonify({"status": "success", "automacao": service._to_dict(a)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/automacoes/<int:automacao_id>", methods=["PUT"])
@check_session
def api_automacoes_update(automacao_id):
    """Atualiza uma automação."""
    data = request.json or {}
    with Session() as db:
        service = AutomacaoService(db)
        try:
            a = service.update_automacao(automacao_id, data)
            return jsonify({"status": "success", "automacao": service._to_dict(a)})
        except ValueError as e:
            return jsonify({"error": str(e)}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/automacoes/<int:automacao_id>", methods=["DELETE"])
@check_session
def api_automacoes_delete(automacao_id):
    """Exclui uma automação."""
    with Session() as db:
        service = AutomacaoService(db)
        try:
            service.delete_automacao(automacao_id)
            return jsonify({"status": "success"})
        except ValueError as e:
            return jsonify({"error": str(e)}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/automacoes/<int:automacao_id>/toggle", methods=["POST"])
@check_session
def api_automacoes_toggle(automacao_id):
    """Ativa/desativa uma automação."""
    with Session() as db:
        service = AutomacaoService(db)
        try:
            ativa = service.toggle_automacao(automacao_id)
            return jsonify({"status": "success", "ativa": ativa})
        except ValueError as e:
            return jsonify({"error": str(e)}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/automacoes/logs", methods=["GET"])
@check_session
def api_automacoes_logs():
    """Lista os logs de execução."""
    automacao_id = request.args.get("automacao_id", type=int)
    limit = request.args.get("limit", 100, type=int)
    with Session() as db:
        service = AutomacaoService(db)
        return jsonify(service.list_logs(limit=limit, automacao_id=automacao_id))


@app.route("/api/automacoes/triggers", methods=["GET"])
@check_session
def api_automacoes_triggers():
    """Retorna os tipos de gatilho disponíveis."""
    from services.automacao_service import TRIGGER_TYPES
    return jsonify(TRIGGER_TYPES)


@app.route("/api/automacoes/variables", methods=["GET"])
@check_session
def api_automacoes_variables():
    """Retorna as variáveis disponíveis para o payload."""
    from services.automacao_service import VARIABLES
    return jsonify(VARIABLES)


@app.route("/api/automacoes/kanban-config", methods=["GET"])
@check_session
def api_automacoes_kanban_config():
    """Retorna as fases do Kanban para configurar gatilhos."""
    slug = request.args.get("slug", "fluxo-projetos")
    with Session() as db:
        service = KanbanService(db)
        config = service.get_board_config(slug)
        fases = config.get("fases", [])
        return jsonify([{"id": f["id"], "nome": f["nome"]} for f in fases])


# ─── HOOKS: Gatilhos de Automação nos eventos do Kanban ─────────────────────

def _disparar_automacoes_card_criado(card_id, card_title, phase_id, phase_name, project_id, project_name, project_date):
    try:
        with Session() as db:
            service = AutomacaoService(db)
            service.trigger_card_created(card_id, card_title, phase_id, phase_name, project_id, project_name, project_date)
    except Exception as e:
        print(f"[automacao] Erro ao disparar trigger card_created: {e}")


def _disparar_automacoes_card_movido(card_id, card_title, old_phase_id, old_phase_name, new_phase_id, new_phase_name, project_id, project_name, project_date):
    try:
        with Session() as db:
            service = AutomacaoService(db)
            service.trigger_card_left_phase(card_id, card_title, old_phase_id, old_phase_name, project_id, project_name, project_date)
            service.trigger_card_entered_phase(card_id, card_title, new_phase_id, new_phase_name, project_id, project_name, project_date)
            service.trigger_card_moved(card_id, card_title, old_phase_id, old_phase_name, new_phase_id, new_phase_name, project_id, project_name, project_date)
    except Exception as e:
        print(f"[automacao] Erro ao disparar trigger card_moved: {e}")


@app.route("/api/ranking", methods=["GET"])
@check_session
def api_ranking():
    """
    Retorna os dados dos investidores e suas métricas para o painel de ranking.
    Busca o registro mais recente (mês/ano atual ou anterior) de cada investidor.
    """
    try:
        from sqlalchemy import func, desc, case
        from datetime import datetime, date
        now = datetime.now()
        mes_atual = now.month
        ano_atual = now.year

        with Session() as db:
            # Busca todos os investidores ativos
            investidores = db.query(Investidor).filter_by(ativo=True).all()
            
            # Busca as métricas do mês atual
            metricas = db.query(MetricaMensal).filter_by(mes=mes_atual, ano=ano_atual).all()
            
            # Se não houver métricas para o mês atual, tenta o mês anterior
            if not metricas:
                mes_busca = 12 if mes_atual == 1 else mes_atual - 1
                ano_busca = ano_atual - 1 if mes_atual == 1 else ano_atual
                metricas = db.query(MetricaMensal).filter_by(mes=mes_busca, ano=ano_busca).all()
            
            metricas_map = {m.email_investidor: m for m in metricas}

            # Map de Churn e Projetos (Novo cálculo real)
            from models import InvestidorProjeto
            churn_data = db.query(
                InvestidorProjeto.email_investidor,
                func.max(InvestidorProjeto.inactivated_at).label('last_churn'),
                func.min(InvestidorProjeto.created_at).label('first_project'),
                func.sum(case((InvestidorProjeto.active == True, 1), else_=0)).label('active_count')
            ).group_by(InvestidorProjeto.email_investidor).all()
            
            churn_map = {c.email_investidor: (c.last_churn, c.first_project, int(c.active_count or 0)) for c in churn_data}
            
            ranking_list = []
            for inv in investidores:
                m = metricas_map.get(inv.email)
                churn_info = churn_map.get(inv.email)
                
                # OBRIGATÓRIO: Ter pelo menos 1 projeto vinculado para aparecer no ranking
                if not churn_info:
                    continue
                # Lógica de Dias Sem Churn:
                days_without_churn = 0
                if churn_info:
                    last_churn, first_project, active_projects = churn_info
                    base_date = last_churn if last_churn else first_project
                    if base_date:
                        d_base = base_date if isinstance(base_date, date) else base_date.date() if hasattr(base_date, 'date') else None
                        if d_base:
                            delta = now.date() - d_base
                            days_without_churn = max(0, delta.days)
                
                # Mapeamento de Senioridade e Level
                raw_level = m.level if m else (inv.nivel or "L1")
                seniority_display = f"{inv.senioridade or 'Investidor'} | {raw_level}"

                # Formatação de MRR (carteira sob gestão — portfolio total)
                mrr_val = float(m.fixo_mrr_projeto_total or 0) if m else 0.0
                mrr_formatted = f"R$ {mrr_val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

                ranking_list.append({
                    "id": inv.id,
                    "email": inv.email,
                    "name": inv.nome,
                    "role": inv.funcao or inv.posicao,
                    "level": seniority_display,
                    "level_raw": raw_level,
                    "flag": m.flag if m else "white",
                    "daysWithoutChurn": days_without_churn,
                    "clientsCount": active_projects,
                    "mrr": mrr_val,
                    "mrr_formatted": mrr_formatted,
                    "tenure": inv.senioridade,
                    "photo": f"static/images/profile_pictures/{inv.profile_picture}" if inv.profile_picture else None,
                    "highlights": m.motivo_flag.split(",") if m and m.motivo_flag else ["Investidor Ativo"]
                })
            
            return jsonify(ranking_list)
            
    except Exception as e:
        print(f"Erro no ranking API: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/hub-cs-cx")
@check_session
@check_access(["Gerência", "Sócio", "Account", "Customer Success"])
def hub_cs_cx():
    view = request.args.get("view", "dashboard")
    client_id = request.args.get("client")
    
    try:
        from sqlalchemy import func
        from datetime import date, datetime
        from services.currency import CurrencyService

        with Session() as db:
            # 1. KPIs Gerais (Dashboard) - Sincronizado com a Home
            usd_rate = float(CurrencyService.get_usd_to_brl_rate())
            
            # 1. KPIs Gerais (Dashboard)
            projetos_todos = db.query(Projeto).filter(Projeto.status.in_(['Ativo', 'Onetime'])).all()
            
            mrr_total = 0
            usd_rate = float(CurrencyService.get_usd_to_brl_rate())
            
            for p in projetos_todos:
                fee_p = float(p.fee or 0)
                if str(p.moeda).strip().upper() == "USD":
                    mrr_total += fee_p * usd_rate
                else:
                    mrr_total += fee_p
            
            active_clients = db.query(Projeto).filter_by(status='Ativo').count()
            nps_avg = db.query(func.avg(OperacaoCheckin.csat_pontuacao)).filter(OperacaoCheckin.csat_pontuacao != None).scalar() or 0
            
            # 2. Ranking: Usando a tabela unificada
            ranking = db.query(Projeto).all()
            today = date.today()
            
            def calculate_meses_to(start_date, end_date):
                if not start_date: return 0
                try:
                    if isinstance(start_date, str):
                        start_date = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
                    if isinstance(start_date, datetime):
                        start_date = start_date.date()
                    if not isinstance(start_date, date):
                        return 0
                    if start_date > end_date: return 0
                    diff = end_date - start_date
                    return max(1, diff.days // 30)
                except:
                    return 0

            for p in ranking:
                p.tempo_de_casa_meses_ranking = calculate_meses_to(p.data_de_inicio, today)
                fee_p = float(p.fee or 0)
                if str(p.moeda).strip().upper() == "USD":
                    p.ltv_real = fee_p * usd_rate * p.tempo_de_casa_meses_ranking
                else:
                    p.ltv_real = fee_p * p.tempo_de_casa_meses_ranking
            
            if view == "detail" and client_id:
                try: cid = int(client_id)
                except: cid = 0

                projetos_cliente = db.query(Projeto).filter(Projeto.pipefy_id == cid).all()
                cliente = projetos_cliente[0] if projetos_cliente else None
                
                if not cliente:
                    return redirect(url_for("hub_cs_cx"))
                
                # Senioridade Real (desde o primeiro projeto histórico com o mesmo nome na tabela unificada)
                data_primeiro = db.query(func.min(Projeto.data_de_inicio)).filter(Projeto.nome == cliente.nome).scalar()
                
                cliente.tempo_de_casa_meses = calculate_meses_to(data_primeiro or cliente.data_de_inicio, today)
                
                # Agrega métricas da conta com conversão
                cliente.mrr_total = 0
                for p in projetos_cliente:
                    fee_p = float(p.fee or 0)
                    if str(p.moeda).strip().upper() == "USD":
                        cliente.mrr_total += fee_p * usd_rate
                    else:
                        cliente.mrr_total += fee_p

                # Cálculo Real de LTV Histórico por Semestre (Todos da tabela unificada para o mesmo cliente)
                todos_historico = db.query(Projeto).filter(Projeto.nome == cliente.nome).all()
                
                labels_ltv = ["2024-S1", "2024-S2", "2025-S1"]
                marcos = [date(2024, 6, 30), date(2024, 12, 31), today]
                dados_ltv = []
                
                for marco in marcos:
                    ltv_no_marco = 0
                    for p in todos_historico:
                        p_fim = p.data_fim if p.data_fim else today
                        data_limite = min(marco, today, p_fim)
                        
                        meses_marco = calculate_meses_to(p.data_de_inicio, data_limite)
                        fee_p = float(p.fee or 0)
                        if str(p.moeda).strip().upper() == "USD":
                            ltv_no_marco += fee_p * usd_rate * meses_marco
                        else:
                            ltv_no_marco += fee_p * meses_marco
                    dados_ltv.append(round(ltv_no_marco, 2))
                
                cliente.ltv_total = dados_ltv[-1]
                cliente.projetos_ativos = projetos_cliente

                equipe = db.query(
                    Investidor.nome, 
                    Investidor.funcao, 
                    Investidor.profile_picture,
                    InvestidorProjeto.cientista
                ).join(Investidor, Investidor.email == InvestidorProjeto.email_investidor)\
                 .filter(InvestidorProjeto.pipefy_id_projeto == cid, InvestidorProjeto.active == True).all()

                # Health Score Dinâmico (Últimas 4 semanas de checkin)
                checkins = db.query(OperacaoCheckin).filter(
                    OperacaoCheckin.projeto_pipefy_id == cid
                ).order_by(OperacaoCheckin.semana_ano.desc()).limit(4).all()
                
                labels_health = ["Sem 1", "Sem 2", "Sem 3", "Sem 4"]
                dados_health = [80] * 4 # Default
                
                if checkins:
                    checkins.reverse()
                    for i, chk in enumerate(checkins):
                        if i < 4:
                            dados_health[i] = chk.csat_pontuacao or 80
                
                return render_template("cs_client_detail.html", 
                                     cliente=cliente, equipe=equipe,
                                     labels_ltv=labels_ltv, dados_ltv=dados_ltv,
                                     labels_health=labels_health, dados_health=dados_health)
            
            return render_template("cs_dashboard.html", 
                                 mrr_total=float(mrr_total),
                                 active_clients=active_clients,
                                 nps_avg=round(float(nps_avg), 1),
                                 ranking=ranking)
                                 
    except Exception as e:
        import traceback
        print(f"Erro crítico no hub-cs-cx: {e}")
        traceback.print_exc()
        return render_template("cs_dashboard.html", mrr_total=0, active_clients=0, nps_avg=0, ranking=[])

@app.route("/cockpit", methods=["GET"])
@check_session
def cockpit():
    return render_template("cockpit.html")


# ─── Formulário Público por Fase (sem login) ────────────────────────────────────

from collections import defaultdict as dd
_form_submission_log = dd(list)
_FORM_LIMIT = 10
_FORM_WINDOW = 3600


def _check_rate_limit(ip: str) -> bool:
    """Verifica se o IP excedeu o limite de submissões."""
    now = dt.utcnow()
    cutoff = now - timedelta(seconds=_FORM_WINDOW)
    _form_submission_log[ip] = [t for t in _form_submission_log[ip] if t > cutoff]
    if len(_form_submission_log[ip]) >= _FORM_LIMIT:
        return False
    _form_submission_log[ip].append(now)
    return True


@app.route("/form-card/<token>", methods=["GET"])
def public_form(token):
    """Página pública do formulário dinâmico de uma fase."""
    from services.kanban_service import KanbanService
    with Session() as db:
        service = KanbanService(db)
        slug, fase = service.find_phase_by_token(token)
        if not fase:
            return render_template("form_card.html", erro="Link inválido ou expirado.", fase=None, board_nome=None)

        config = service.get_board_config(slug)
        board_nome = config.get("nome", slug)
        return render_template("form_card.html", fase=fase, board_nome=board_nome, token=token, erro=None)


@app.route("/form-card/<token>", methods=["POST"])
def public_form_submit(token):
    """Processa o envio do formulário público."""
    from services.kanban_service import KanbanService

    ip = request.remote_addr or "desconhecido"
    if not _check_rate_limit(ip):
        return render_template("form_card.html", erro="Limite de envios atingido. Tente novamente mais tarde.", fase=None, board_nome=None)

    honeypot = request.form.get("_hp", "")
    if honeypot:
        return render_template("form_card.html", erro="Envio suspeito.", fase=None, board_nome=None)

    with Session() as db:
        service = KanbanService(db)
        slug, fase = service.find_phase_by_token(token)
        if not fase:
            return render_template("form_card.html", erro="Link inválido.", fase=None, board_nome=None)

        nome = (request.form.get("nome_projeto") or "").strip()
        if not nome:
            config = service.get_board_config(slug)
            board_nome = config.get("nome", slug)
            return render_template("form_card.html", erro="O nome do projeto é obrigatório.", fase=fase, board_nome=board_nome, token=token)

        dados = {}
        fase_nome = fase['nome']
        for campo in fase.get('campos', []):
            raw = request.form.get(f"campo_{campo['id']}", "")
            if campo['tipo'] == 'checkbox':
                # multiple values
                vals = request.form.getlist(f"campo_{campo['id']}")
                dados[campo['id']] = vals
            elif campo['tipo'] == 'boolean':
                dados[campo['id']] = raw == "true"
            elif campo['tipo'] == 'number':
                try:
                    if raw:
                        raw = raw.replace(',', '.')
                    dados[campo['id']] = float(raw) if raw else None
                except ValueError:
                    dados[campo['id']] = raw
            else:
                dados[campo['id']] = raw

            if campo.get('obrigatorio'):
                val = dados.get(campo['id'])
                if val is None or (isinstance(val, str) and not val.strip()) or (isinstance(val, list) and len(val) == 0):
                    config = service.get_board_config(slug)
                    board_nome = config.get("nome", slug)
                    return render_template("form_card.html", erro=f"O campo '{campo['label']}' é obrigatório.", fase=fase, board_nome=board_nome, token=token)

        dados['_origem_formulario'] = fase_nome
        usuario_email = f"formulario@{slug}.externo"

        try:
            projeto = service.create_card_in_phase(slug, fase, nome, dados, usuario_email)
            return render_template("form_card.html", sucesso=True, fase=fase, board_nome=service.get_board_config(slug).get("nome", slug))
        except Exception as e:
            config = service.get_board_config(slug)
            board_nome = config.get("nome", slug)
            return render_template("form_card.html", erro=f"Erro ao criar card: {str(e)}", fase=fase, board_nome=board_nome, token=token)


# ─── FACE AUTH ───────────────────────────────────────────────────────────────

FACE_CAPTURE_MIN_FRAMES = 8
FACE_RATE_LIMIT_MAX_ATTEMPTS = 5
FACE_RATE_LIMIT_WINDOW = 15
_face_rate_limit_store = {}

def _check_face_rate_limit(email):
    now = dt.now()
    if email not in _face_rate_limit_store:
        _face_rate_limit_store[email] = []
    _face_rate_limit_store[email] = [
        t for t in _face_rate_limit_store[email]
        if (now - t).total_seconds() < FACE_RATE_LIMIT_WINDOW * 60
    ]
    return len(_face_rate_limit_store[email]) < FACE_RATE_LIMIT_MAX_ATTEMPTS


def _increment_face_rate_limit(email):
    _face_rate_limit_store.setdefault(email, []).append(dt.now())


def _log_face_auth(db, email, event_type, status, similarity=None, samples=None, error_message=None):
    user = db.query(Investidor).filter_by(email=email).first() if email else None
    log_entry = FaceAuthLog(
        user_id=getattr(user, 'id', None) if user else None,
        email=email,
        event_type=event_type,
        status=status,
        similarity=f"{similarity:.4f}" if similarity is not None else None,
        samples=samples,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")[:500],
        error_message=error_message
    )
    db.add(log_entry)


@app.route("/api/face/biometry/status", methods=["GET"])
@check_session
def face_biometry_status():
    email = session.get("email")
    if not email:
        return jsonify({"error": "Usuário não autenticado"}), 401
    try:
        with Session() as db:
            user = db.query(Investidor).filter_by(email=email).first()
            if not user:
                return jsonify({"error": "Usuário não encontrado"}), 404
            faces = db.query(UserFace).filter_by(user_id=user.id, is_active=True).all()
            return jsonify({
                "has_biometry": len(faces) > 0,
                "total_faces": len(faces),
                "last_registration": faces[0].created_at.isoformat() if faces else None,
                "total_samples": sum(f.samples or 0 for f in faces) if faces else 0
            })
    except SQLAlchemyError as e:
        print(f"[FaceAuth] Erro ao consultar status: {e}")
        return jsonify({"error": "Erro ao consultar status da biometria"}), 500


@app.route("/api/face/biometry/register", methods=["POST"])
@check_session
def face_biometry_register():
    email = session.get("email")
    if not email:
        return jsonify({"error": "Usuário não autenticado"}), 401
    data = request.get_json()
    if not data or "frames" not in data:
        return jsonify({"error": "Nenhum frame enviado"}), 400
    frames = data["frames"]
    if len(frames) < FACE_CAPTURE_MIN_FRAMES:
        return jsonify({"error": f"Mínimo de {FACE_CAPTURE_MIN_FRAMES} frames necessários. Enviados: {len(frames)}"}), 400
    from face_auth.face_service import process_frames_for_biometric_registration
    try:
        result = process_frames_for_biometric_registration(frames)
    except Exception as e:
        print(f"[FaceAuth] Erro no processamento facial: {e}")
        return jsonify({"error": f"Erro ao processar frames: {str(e)}"}), 500
    if not result["success"]:
        return jsonify({"error": result["error"]}), 400
    try:
        with Session() as db:
            user = db.query(Investidor).filter_by(email=email).first()
            if not user:
                return jsonify({"error": "Usuário não encontrado"}), 404
            new_face = UserFace(
                user_id=user.id,
                embedding=result["embedding"],
                is_active=True,
                samples=result["samples"],
                created_at=dt.now()
            )
            db.add(new_face)
            _log_face_auth(db, email, "REGISTER", "SUCCESS",
                           samples=result["samples"])
            db.commit()
            return jsonify({
                "success": True,
                "message": "Biometria facial cadastrada com sucesso.",
                "samples": result["samples"],
                "liveness_score": result.get("liveness_score", 0)
            })
    except SQLAlchemyError as e:
        print(f"[FaceAuth] Erro ao salvar biometria: {e}")
        return jsonify({"error": "Erro ao salvar biometria no banco"}), 500


@app.route("/api/face/biometry/update", methods=["POST"])
@check_session
def face_biometry_update():
    email = session.get("email")
    if not email:
        return jsonify({"error": "Usuário não autenticado"}), 401
    data = request.get_json()
    if not data or "frames" not in data:
        return jsonify({"error": "Nenhum frame enviado"}), 400
    frames = data["frames"]
    if len(frames) < FACE_CAPTURE_MIN_FRAMES:
        return jsonify({"error": f"Mínimo de {FACE_CAPTURE_MIN_FRAMES} frames necessários. Enviados: {len(frames)}"}), 400
    from face_auth.face_service import process_frames_for_biometric_registration
    try:
        result = process_frames_for_biometric_registration(frames)
    except Exception as e:
        print(f"[FaceAuth] Erro no processamento facial: {e}")
        return jsonify({"error": f"Erro ao processar frames: {str(e)}"}), 500
    if not result["success"]:
        return jsonify({"error": result["error"]}), 400
    try:
        with Session() as db:
            user = db.query(Investidor).filter_by(email=email).first()
            if not user:
                return jsonify({"error": "Usuário não encontrado"}), 404
            faces = db.query(UserFace).filter_by(user_id=user.id, is_active=True).all()
            for face in faces:
                face.is_active = False
            new_face = UserFace(
                user_id=user.id,
                embedding=result["embedding"],
                is_active=True,
                samples=result["samples"],
                created_at=dt.now()
            )
            db.add(new_face)
            _log_face_auth(db, email, "UPDATE", "SUCCESS",
                           samples=result["samples"])
            db.commit()
            return jsonify({
                "success": True,
                "message": "Biometria facial atualizada com sucesso.",
                "samples": result["samples"],
                "liveness_score": result.get("liveness_score", 0)
            })
    except SQLAlchemyError as e:
        print(f"[FaceAuth] Erro ao atualizar biometria: {e}")
        return jsonify({"error": "Erro ao atualizar biometria no banco"}), 500


@app.route("/api/face/biometry/delete", methods=["POST"])
@check_session
def face_biometry_delete():
    email = session.get("email")
    if not email:
        return jsonify({"error": "Usuário não autenticado"}), 401
    try:
        with Session() as db:
            user = db.query(Investidor).filter_by(email=email).first()
            if not user:
                return jsonify({"error": "Usuário não encontrado"}), 404
            faces = db.query(UserFace).filter_by(user_id=user.id, is_active=True).all()
            if not faces:
                return jsonify({"error": "Nenhuma biometria encontrada"}), 404
            for face in faces:
                db.delete(face)
            _log_face_auth(db, email, "DELETE", "SUCCESS")
            db.commit()
            return jsonify({"success": True, "message": "Biometria facial removida com sucesso."})
    except SQLAlchemyError as e:
        print(f"[FaceAuth] Erro ao remover biometria: {e}")
        return jsonify({"error": "Erro ao remover biometria"}), 500


@app.route("/api/face/login/check", methods=["POST"])
def face_login_check():
    from face_auth.face_service import get_face_analysis
    get_face_analysis()
    data = request.get_json()
    if not data or "email" not in data:
        return jsonify({"error": "Email não informado"}), 400
    email = data["email"]
    try:
        with Session() as db:
            user = db.query(Investidor).filter_by(email=email).first()
            if not user or user.ativo is not True:
                return jsonify({"has_face_biometry": False, "user_exists": False}), 200
            faces = db.query(UserFace).filter_by(user_id=user.id, is_active=True).count()
            return jsonify({
                "has_face_biometry": faces > 0,
                "user_exists": True,
                "name": user.nome
            })
    except SQLAlchemyError as e:
        print(f"[FaceAuth] Erro ao verificar biometria: {e}")
        return jsonify({"error": "Erro ao verificar disponibilidade facial"}), 500


@app.route("/api/face/login/authenticate", methods=["POST"])
def face_login_authenticate():
    data = request.get_json()
    if not data or "email" not in data or "frame" not in data:
        return jsonify({"error": "Dados incompletos"}), 400
    email = data["email"]
    frame_b64 = data["frame"]
    if not _check_face_rate_limit(email):
        return jsonify({"error": "Muitas tentativas. Aguarde 15 minutos."}), 429
    from face_auth.face_service import process_login_frame, match_face
    result = process_login_frame(frame_b64)
    if not result["success"]:
        return jsonify({"error": result["error"]}), 400
    try:
        with Session() as db:
            user = db.query(Investidor).filter_by(email=email).first()
            if not user or user.ativo is not True:
                _log_face_auth(db, email, "LOGIN", "FAILURE",
                               error_message="Usuário não encontrado ou inativo")
                db.commit()
                return jsonify({"error": "Usuário não encontrado ou inativo"}), 401
            faces = db.query(UserFace).filter_by(user_id=user.id, is_active=True).all()
            if not faces:
                _log_face_auth(db, email, "LOGIN", "FAILURE",
                               error_message="Nenhuma biometria cadastrada")
                db.commit()
                return jsonify({"error": "Nenhuma biometria cadastrada"}), 401
            stored_embeddings = [f.embedding for f in faces]
            match_result = match_face(result["embedding"], stored_embeddings)
            if match_result["match"]:
                token = os.urandom(10).hex()
                auth_entry = db.get(Auth, user.email)
                if auth_entry:
                    auth_entry.token = token
                else:
                    max_id = db.query(Auth.id).order_by(Auth.id.desc()).first()
                    auth_entry = Auth(id=(max_id[0] + 1) if max_id else 1,
                                      email=user.email, token=token)
                    db.add(auth_entry)
                db.commit()
                session["nome"] = user.nome
                session["email"] = user.email
                session["token"] = token
                session["funcao"] = user.funcao
                session["posicao"] = user.posicao
                session["senioridade"] = user.senioridade
                session["squad"] = user.squad
                session["nivel_acesso"] = user.nivel_acesso
                session["pode_editar_kanban"] = user.pode_editar_kanban
                session["profile_picture"] = user.profile_picture
                _log_face_auth(db, email, "LOGIN", "SUCCESS",
                               similarity=match_result["similarity"])
                db.commit()
                return jsonify({
                    "success": True,
                    "message": "Autenticação facial bem-sucedida.",
                    "similarity": match_result["similarity"],
                    "redirect": url_for("home")
                })
            else:
                _increment_face_rate_limit(email)
                _log_face_auth(db, email, "LOGIN", "FAILURE",
                               similarity=match_result["similarity"],
                               error_message=f"Similaridade {match_result['similarity']:.4f} abaixo do threshold")
                db.commit()
                return jsonify({
                    "error": "Rosto não reconhecido.",
                    "similarity": match_result["similarity"],
                    "threshold": match_result["threshold"]
                }), 401
    except SQLAlchemyError as e:
        print(f"[FaceAuth] Erro na autenticação facial: {e}")
        return jsonify({"error": "Erro ao processar autenticação facial"}), 500


@app.route("/api/face/login/capture-and-auth", methods=["POST"])
def face_login_capture_and_auth():
    data = request.get_json()
    if not data or "email" not in data or "frames" not in data:
        return jsonify({"error": "Dados incompletos"}), 400
    email = data["email"]
    frames = data["frames"]
    if not _check_face_rate_limit(email):
        return jsonify({"error": "Muitas tentativas. Aguarde 15 minutos."}), 429
    from face_auth.face_service import process_frames_for_biometric_registration, process_login_frame, match_face
    liveness_result = process_frames_for_biometric_registration(frames)
    if not liveness_result["success"]:
        return jsonify({"error": liveness_result["error"]}), 400
    avg_embedding = liveness_result["embedding"]
    try:
        with Session() as db:
            user = db.query(Investidor).filter_by(email=email).first()
            if not user or user.ativo is not True:
                _log_face_auth(db, email, "LOGIN", "FAILURE",
                               error_message="Usuário não encontrado ou inativo")
                db.commit()
                return jsonify({"error": "Usuário não encontrado ou inativo"}), 401
            faces = db.query(UserFace).filter_by(user_id=user.id, is_active=True).all()
            if not faces:
                _log_face_auth(db, email, "LOGIN", "FAILURE",
                               error_message="Nenhuma biometria cadastrada")
                db.commit()
                return jsonify({"error": "Nenhuma biometria cadastrada"}), 401
            stored_embeddings = [f.embedding for f in faces]
            match_result = match_face(avg_embedding, stored_embeddings)
            if match_result["match"]:
                token = os.urandom(10).hex()
                auth_entry = db.get(Auth, user.email)
                if auth_entry:
                    auth_entry.token = token
                else:
                    max_id = db.query(Auth.id).order_by(Auth.id.desc()).first()
                    auth_entry = Auth(id=(max_id[0] + 1) if max_id else 1,
                                      email=user.email, token=token)
                    db.add(auth_entry)
                db.commit()
                session["nome"] = user.nome
                session["email"] = user.email
                session["token"] = token
                session["funcao"] = user.funcao
                session["posicao"] = user.posicao
                session["senioridade"] = user.senioridade
                session["squad"] = user.squad
                session["nivel_acesso"] = user.nivel_acesso
                session["pode_editar_kanban"] = user.pode_editar_kanban
                session["profile_picture"] = user.profile_picture
                _log_face_auth(db, email, "LOGIN", "SUCCESS",
                               similarity=match_result["similarity"],
                               samples=len(frames))
                db.commit()
                return jsonify({
                    "success": True,
                    "message": "Autenticação facial bem-sucedida.",
                    "similarity": match_result["similarity"],
                    "redirect": url_for("home")
                })
            else:
                _increment_face_rate_limit(email)
                _log_face_auth(db, email, "LOGIN", "FAILURE",
                               similarity=match_result["similarity"],
                               samples=len(frames),
                               error_message=f"Similaridade {match_result['similarity']:.4f} abaixo do threshold")
                db.commit()
                return jsonify({
                    "error": "Rosto não reconhecido.",
                    "similarity": match_result["similarity"],
                    "threshold": match_result["threshold"]
                }), 401
    except SQLAlchemyError as e:
        print(f"[FaceAuth] Erro na autenticação facial: {e}")
        return jsonify({"error": "Erro ao processar autenticação facial"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
