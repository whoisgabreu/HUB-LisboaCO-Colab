from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from flask_apscheduler import APScheduler
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from collections import defaultdict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime as dt
import os
import json

from database import Session, engine, Base
from models import (
    Investidor, Auth, ProjetoAtivo, ProjetoOnetime, ProjetoInativo,
    MetricaMensal, InvestidorProjeto,
    OperacaoTarefa, OperacaoEntregaMensal, OperacaoPlanoMidia,
    OperacaoOtimizacao, OperacaoCheckin,
    MonthlyDelivery, OperacaoLinkUtil, EntregaCriativa,
)
from services.remuneracao import calcular_metricas_mensais
from services.operacao_service import OperacaoService, OperacaoSnapshotService
from services.projeto_participacao_service import ProjetoParticipacaoService




app = Flask(__name__)
app.secret_key = os.urandom(10).hex()

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
            
            # Se for Gerência, Sócio ou Coordenador via posição, concede acesso a quase tudo
            is_high_level = user_posicao in ["Gerência", "Sócio", "Coordenador"]
            
            # Verifica se o cargo solicitado está na lista ou se é Gerência/Sócio
            if not is_high_level and not any(role.lower() == user_role.lower() for role in roles):
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
    ).first()
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

def _recalcular_mrr_por_entregas(record):
    """
    Recalcula os campos de MRR no MetricaMensal após o registro de uma entrega.
    Garante que fixo_mrr_entrega, fixo_mrr_atual, fixo_churn_atual e
    fixo_mrr_projeto_total fiquem sempre consistentes entre si.
    O banco usa fixo_mrr_atual (entregue - churn) para todas as fórmulas GENERATED.
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

    with Session() as db_aux:
        # Busca todos os vínculos (ativos + inativados no mês para churn)
        from sqlalchemy import or_, and_, extract
        todos_vinculos = db_aux.query(InvestidorProjeto).filter(
            InvestidorProjeto.email_investidor == record.email_investidor
        ).all()

        usd_rate = None  # carregado uma vez se necessário

        for v in todos_vinculos:
            pid = str(v.pipefy_id_projeto)

            from models import ProjetoAtivo, ProjetoOnetime, ProjetoInativo
            proj = db_aux.query(ProjetoAtivo).filter_by(pipefy_id=v.pipefy_id_projeto).first()
            if not proj:
                proj = db_aux.query(ProjetoOnetime).filter_by(pipefy_id=v.pipefy_id_projeto).first()
            if not proj:
                proj = db_aux.query(ProjetoInativo).filter_by(pipefy_id=v.pipefy_id_projeto).first()
                
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
                # valor_proporcional está na moeda original — precisa converter USD→BRL
                fee = Decimal(str(proj_hist["valor_proporcional"]))
                if moeda_proj == "USD" and usd_rate:
                    fee *= usd_rate
                fee = fee.quantize(Decimal("0.01"))
            else:
                fee = fee_full  # sem histórico proporcional, usa fee completo

            if v.active:
                mrr_portfolio_total += fee_full  # portfolio = fees completos
                
                # Detalhes (snapshot para o JSON)
                novos_detalhes.append({
                    "id": v.pipefy_id_projeto,
                    "nome": v.nome_projeto,
                    "moeda": moeda_proj,
                    "cientista": bool(v.cientista),
                    "ativo": True,
                    "fee": float(fee_full)
                })

                # Regra: Meses 02 e 03 de 2026 estão zerados para todos (nenhuma entrega)
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
                            # Cap por categoria: entrega acima do contratado não conta no MRR
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

            else:
                # Churn: apenas vinculos inativados no mês deste record
                if v.inactivated_at and v.inactivated_at.strftime("%Y-%m") == mes_atual_str:
                    churn_calculado += fee
                    # Portfólio Total deve incluir quem saiu no mês também!
                    mrr_portfolio_total += fee_full
                    
                    # Detalhes do Churn (snapshot para o JSON)
                    novos_detalhes.append({
                        "id": v.pipefy_id_projeto,
                        "nome": v.nome_projeto,
                        "moeda": moeda_proj,
                        "cientista": bool(v.cientista),
                        "ativo": False,
                        "churned": True,
                        "data_churn": v.inactivated_at.strftime("%d/%m/%Y"),
                        "fee": float(fee_full)
                    })

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
        "plano_midia":      {"budget_total": 0, "planos": []},
        "otimizacoes":      [],
        "forecasting":      {"link": ""},
        "kpis":             {"link": ""},
        "checkin_semanal":  [],
        "relatorio_mensal": {"link": ""},
        "metas":            {},
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
                proj = (ndb.query(ProjetoAtivo).filter_by(pipefy_id=pipefy_id).first()
                        or ndb.query(ProjetoOnetime).filter_by(pipefy_id=pipefy_id).first())
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
        now = _dt.now()
        if ano < now.year or (ano == now.year and mes < now.month):
            return

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
                    p_ativo = db.query(ProjetoAtivo).filter_by(pipefy_id=pipefy_id).first()
                    proj_name = p_ativo.nome if p_ativo else f"Projeto {pipefy_id}"

                entry = _build_entrega_op_entry(pipefy_id, proj_name, hint)
                lista.append(entry)
                metrica.entregas_operacao = lista
                # Não retornamos, continuamos para preencher os counts no novo entry

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

            links = {}
            if kpis_link:
                links["link_kpi"] = kpis_link
            if forecasting_link:
                links["link_forecast"] = forecasting_link
            if relatorio_link:
                links["link_relatorio"] = relatorio_link

            # Contabilizar tarefas semanais (planner_monday)
            tarefas_snap = snap.get("tarefas_semanais") or []
            count_semanal = len(tarefas_snap)
            if count_semanal == 0:
                # Fallback para tabela antiga — SAVEPOINT protege a sessão
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
                    # Tabela operacao_tarefas pode não existir — nested.rollback salva o restante da transação
                    try:
                        nested.rollback()
                    except Exception:
                        pass
                    print(f"[metrica sync] tabela operacao_tarefas indisponível, ignorando fallback")
                    count_semanal = 0
            counts["planner_monday"] = min(count_semanal, 4)

            # Mapa de metas corretas baseado nos templates oficiais
            _metas_corretas = {}
            for tpl in _ENTREGAS_ACCOUNT_TPL + _ENTREGAS_GT_TPL:
                _metas_corretas[tpl["nome"]] = tpl["meta"]

            changed = False
            for ent in entry.get("entregas", []):
                n = ent.get("nome")
                if n in counts and ent.get("entregues") != counts[n]:
                    ent["entregues"] = counts[n]
                    changed = True
                # Corrigir meta desatualizada (ex: csat_checkin era 1, agora é 4)
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
                _recalcular_mrr_por_entregas(metrica)
                db.commit()
                print(f"[metrica sync] OK {email} projeto={pipefy_id} counts={counts}")
            else:
                print(f"[metrica sync] sem mudancas {email} projeto={pipefy_id}")
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[metrica sync] ERRO: {e}")


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
        "ekyte_workspace": projeto.ekyte_workspace,
        "extra": projeto.extra or {},
        "notas": projeto.notas or {},
    }


def _agrupar_por_cliente(projetos_lista):
    """Agrupa projetos por nome do cliente, ordenados por id (replica lógica do hub_projetos original)."""
    projetos_ordenados = sorted(projetos_lista, key=lambda x: x.get("id", 0))
    clientes = defaultdict(list)
    for projeto in projetos_ordenados:
        cliente_nome = projeto.get("nome", "Cliente Desconhecido")
        clientes[cliente_nome].append(projeto)
    return dict(clientes)


def _buscar_projetos_db(model_class, email_investidor, squad_usuario):
    """Busca projetos no banco com a lógica do n8n: Gerência vê tudo, outros veem só o seu squad."""
    try:
        with Session() as db:
            u_posicao = session.get("posicao")
            if squad_usuario == "Gerência" or u_posicao in ["Gerência", "Sócio"]:
                projetos = db.query(model_class).all()
            elif u_posicao == "Coordenador":
                # Coordenador só vê dados da sua Squad; sem Squad, não vê nada
                if not squad_usuario:
                    return []
                projetos = db.query(model_class).filter_by(squad_atribuida=squad_usuario).all()
            else:
                projetos = db.query(model_class).filter_by(squad_atribuida=squad_usuario).all()
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
                    session["profile_picture"] = user.profile_picture

                    print(session)

                    return redirect(url_for("home"))

            except SQLAlchemyError as e:
                print(f"Erro de banco no login: {e}")
                return render_template("login.html", error="Erro ao conectar ao banco de dados.")

    return render_template("login.html")


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
            clients_count = db.query(ProjetoAtivo).count()
            investors_count = db.query(Investidor).count()
            squads_count = db.query(ProjetoAtivo.squad_atribuida).filter(
                ProjetoAtivo.squad_atribuida != None, 
                ProjetoAtivo.squad_atribuida != ""
            ).distinct().count()

            # MRR Global: Ativos + Onetime
            projetos_ativos = db.query(ProjetoAtivo).all()
            projetos_onetime = db.query(ProjetoOnetime).all()
            projetos = projetos_ativos + projetos_onetime
            
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
                for table in [ProjetoAtivo, ProjetoOnetime, ProjetoInativo]:
                    rows = db.query(table.pipefy_id, table.moeda).all()
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
                projetos_squad = db.query(ProjetoAtivo).all()
            elif u_posicao == "Coordenador":
                # Coordenador só vê sua própria squad; se não tiver squad, não vê nada
                if not squad:
                    projetos_squad = []
                else:
                    projetos_squad = db.query(ProjetoAtivo).filter_by(squad_atribuida=squad).all()
            else:
                projetos_squad = db.query(ProjetoAtivo).filter_by(squad_atribuida=squad).all()
            squads = list(set(p.squad_atribuida for p in projetos_squad if p.squad_atribuida))
    except SQLAlchemyError as e:
        print(f"Erro ao buscar squads: {e}")
        squads = []

    ativos_data = _buscar_projetos_db(ProjetoAtivo, email, squad)
    ativos = _agrupar_por_cliente(ativos_data)

    onetime_data = _buscar_projetos_db(ProjetoOnetime, email, squad)
    onetime = _agrupar_por_cliente(onetime_data)

    inativos_data = _buscar_projetos_db(ProjetoInativo, email, squad)
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
            from models import ProjetoAtivo, ProjetoOnetime, ProjetoInativo
            projeto_metadata = {}
            for table in [ProjetoAtivo, ProjetoOnetime, ProjetoInativo]:
                rows = db.query(table.pipefy_id, table.moeda).all()
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
            from models import ProjetoOnetime, ProjetoInativo
            fee_rows_ativos = db.query(ProjetoAtivo.pipefy_id, ProjetoAtivo.fee, ProjetoAtivo.moeda).all()
            fee_rows_onetime = db.query(ProjetoOnetime.pipefy_id, ProjetoOnetime.fee, ProjetoOnetime.moeda).all()
            fee_rows_inativo = db.query(ProjetoInativo.pipefy_id, ProjetoInativo.fee, ProjetoInativo.moeda).all()
            
            all_fee_rows = fee_rows_ativos + fee_rows_onetime + fee_rows_inativo
            
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
            _recalcular_mrr_por_entregas(record)
            db.commit()
            db.refresh(record)

            remu_atualizada = {
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
            return jsonify({"ok": True, "entregas_criativos": lista, "remu": remu_atualizada})
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
        # Determinar mes/ano a partir da referência
        if referencia and "-M" in referencia:
            parts = referencia.split("-M")
            ano, mes = int(parts[0]), int(parts[1])
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
@check_access(["Account", "Cientista"])
def delete_tarefa_manual():
    """Remove o último registro manual do Planner Monday do mês atual."""
    data = request.json or {}
    pipefy_id = data.get("pipefy_id")
    if not pipefy_id:
        return jsonify({"error": "pipefy_id obrigatório"}), 400

    now = dt.now()
    mes, ano = now.month, now.year
    email = session.get("email")

    try:
        snap = _operacao_get_snapshot(pipefy_id, mes, ano)
        if not snap or "tarefas_semanais" not in snap:
            return jsonify({"error": "Nenhum registro encontrado"}), 404
        
        lst = list(snap["tarefas_semanais"])
        if not lst:
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
        with Session() as db:
            record = db.query(MetricaMensal).filter_by(
                email_investidor=email, mes=mes, ano=ano
            ).first()
            return jsonify(record.entregas_operacao if record else [])
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


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
            _recalcular_mrr_por_entregas(record)
            db.commit()
            db.refresh(record)
            
            remu_atualizada = {
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
            return jsonify({"ok": True, "entregas_operacao": lista, "remu": remu_atualizada})
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
            record = _get_or_create_entrega_record(db, email, int(mes), int(ano))
            lista = _update_entrega_op_links(
                list(record.entregas_operacao or []),
                projeto_id, cliente_nome, responsavel,
                link_relatorio, link_kpi, link_forecast
            )
            record.entregas_operacao = lista
            flag_modified(record, "entregas_operacao")
            _recalcular_mrr_por_entregas(record)
            db.commit()
            return jsonify({"ok": True, "entregas_operacao": lista})
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
    """Calcula entregas concluídas baseado no snapshot da tabela operacao."""
    try:
        snap = _operacao_get_snapshot(pipefy_id, mes, ano)
        if not snap:
            return jsonify([])

        deliveries = []
        idx = 0

        # Plano de mídia — meta 1
        planos = (snap.get("plano_midia") or {}).get("planos") or []
        if planos:
            idx += 1
            deliveries.append({
                "id": idx, "role": "Gestor de Tráfego",
                "delivery_type": "plano_midia", "status": "completed",
                "count": 1,
                "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
            })

        # Otimizações — meta 4
        otims = snap.get("otimizacoes") or []
        cnt_otim = len(otims)
        idx += 1
        deliveries.append({
            "id": idx, "role": "Gestor de Tráfego",
            "delivery_type": "otimizacao",
            "status": "completed" if cnt_otim >= 4 else ("partial" if cnt_otim > 0 else "pending"),
            "count": min(cnt_otim, 4),
            "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
        })

        # Checkin — meta 4
        checkins = snap.get("checkin_semanal") or []
        cnt_checkin = len(checkins)
        idx += 1
        deliveries.append({
            "id": idx, "role": "Account",
            "delivery_type": "checkin",
            "status": "completed" if cnt_checkin >= 4 else ("partial" if cnt_checkin > 0 else "pending"),
            "count": min(cnt_checkin, 4),
            "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
        })

        # Forecasting — meta 1
        if (snap.get("forecasting") or {}).get("link"):
            idx += 1
            deliveries.append({
                "id": idx, "role": "Account",
                "delivery_type": "forecasting", "status": "completed",
                "count": 1,
                "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
            })

        # KPIs — meta 1
        if (snap.get("kpis") or {}).get("link"):
            idx += 1
            deliveries.append({
                "id": idx, "role": "Gestor de Tráfego",
                "delivery_type": "kpis", "status": "completed",
                "count": 1,
                "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
            })

        # Relatórios Mensais (qualquer tipo serve para preencher)
        has_any_report = (
            (snap.get("relatorio_mensal") or {}).get("link") or
            (snap.get("relatorio_gt") or {}).get("link") or
            (snap.get("relatorio_account") or {}).get("link")
        )
        if has_any_report:
            # Emite os três tipos para garantir compatibilidade com qualquer perfil no frontend
            idx += 1
            deliveries.append({
                "id": idx, "role": "Gestor de Tráfego",
                "delivery_type": "relatorio_mensal", "status": "completed",
                "count": 1, "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
            })
            idx += 1
            deliveries.append({
                "id": idx, "role": "Gestor de Tráfego",
                "delivery_type": "relatorio_gt", "status": "completed",
                "count": 1, "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
            })
            idx += 1
            deliveries.append({
                "id": idx, "role": "Account",
                "delivery_type": "relatorio_account", "status": "completed",
                "count": 1, "fee_snapshot": 0, "mrr_contribution": 0, "completed_at": None,
            })

        # Planner Monday — meta 4
        tarefas_semanais = snap.get("tarefas_semanais") or []
        cnt_monday = len(tarefas_semanais)
        idx += 1
        deliveries.append({
            "id": idx, "role": "Account",
            "delivery_type": "planner_monday",
            "status": "completed" if cnt_monday >= 4 else ("partial" if cnt_monday > 0 else "pending"),
            "count": min(cnt_monday, 4),
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
        projeto = db.get(ProjetoAtivo, pipefy_id)
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
            metrica = OperacaoSnapshotService.sync_to_metrica(
                db, email, pipefy_id, int(mes), int(ano)
            )
            if metrica:
                _recalcular_mrr_por_entregas(metrica)
            db.commit()
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
@check_access(["Account", "Cientista", "Gerência", "Desenvolvedor"])
def save_checkin():
    """Salva checkin APENAS na tabela operacao.entregas.checkin_semanal (append)."""
    data = request.json or {}
    email = session.get("email")
    pipefy_id = data.get("pipefy_id")
    now = dt.now()
    mes, ano = now.month, now.year

    print(f"[checkin POST] email={email} projeto={pipefy_id} mes={mes} ano={ano}")

    checkin_snap = {
        "data": now.strftime("%Y-%m-%d"),
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
    """Retorna investidores vinculados a um projeto, com data_inicio resolvida."""
    try:
        with Session() as db:
            vinculos = db.query(InvestidorProjeto).filter_by(pipefy_id_projeto=pipefy_id).all()

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
                result.append({
                    "id": v.id,
                    "email": v.email_investidor,
                    "cientista": v.cientista,
                    "active": v.active,
                    "fee_contribuicao": float(v.fee_contribuicao or 0),
                    "data_inicio": data_inicio
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
                projeto = db.query(ProjetoAtivo).filter_by(pipefy_id=str(pipefy_id)).first()
                if not projeto:
                    projeto = db.query(ProjetoOnetime).filter_by(pipefy_id=str(pipefy_id)).first()
                
                if not projeto or projeto.squad_atribuida != user_squad:
                    return jsonify({"error": "Acesso restrito à sua Squad."}), 403
        except SQLAlchemyError:
            pass # Continua para a lógica principal que lidará com erros de banco
    
    if not email_investidor or not pipefy_id:
        return jsonify({"error": "E-mail e ID do projeto são obrigatórios."}), 400

    try:
        with Session() as db:
            # Busca dados do projeto para denormalização
            projeto = db.query(ProjetoAtivo).filter_by(pipefy_id=pipefy_id).first()
            if not projeto:
                projeto = db.query(ProjetoOnetime).filter_by(pipefy_id=pipefy_id).first()
            
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
            projeto = db.query(ProjetoAtivo).filter_by(pipefy_id=pipefy_id).first()
            is_onetime = False
            is_inativo = False
            if not projeto:
                projeto = db.query(ProjetoOnetime).filter_by(pipefy_id=pipefy_id).first()
                is_onetime = True
            
            if not projeto:
                projeto = db.query(ProjetoInativo).filter_by(pipefy_id=pipefy_id).first()
                is_inativo = True
            
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
                
                # Parse da data_inicio enviada pelo front (YYYY-MM-DD)
                data_inicio_str = inv_data.get("data_inicio")
                from datetime import date as date_type
                if data_inicio_str:
                    try:
                        data_inicio_obj = date_type.fromisoformat(data_inicio_str)
                    except ValueError:
                        data_inicio_obj = None
                else:
                    data_inicio_obj = None

                if v:
                    # Atualiza existente
                    v.nome_projeto = data.get("nome", v.nome_projeto)
                    v.fee_projeto = Decimal(str(data.get("fee", v.fee_projeto) or 0))
                    v.cientista = cientista
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
                                    item["data_inicio"] = data_inicio_str
                                    atualizado = True
                                novo_hist.append(item)
                            if atualizado:
                                metrica.historico_projetos = novo_hist
                                flag_modified(metrica, "historico_projetos")
                else:
                    # Cria novo — usa data_inicio se fornecida, senão hoje
                    created = data_inicio_obj if data_inicio_obj else dt.now().date()
                    novo_v = InvestidorProjeto(
                        pipefy_id_projeto=pipefy_id,
                        email_investidor=email,
                        nome_projeto=data.get("nome", projeto.nome),
                        fee_projeto=Decimal(str(data.get("fee", projeto.fee) or 0)),
                        cientista=cientista,
                        active=True,
                        created_at=created
                    )
                    db.add(novo_v)

            db.commit()
            
            # Sincroniza a remuneração imediatamente para refletir as mudanças no histórico proporcional
            try:
                ProjetoParticipacaoService.sincronizar_remuneracao(dt.now().month, dt.now().year)
            except Exception as e:
                print(f"Erro na sincronização pós-update: {e}")

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
    ativos = _buscar_projetos_db(ProjetoAtivo, email, squad)
    onetime = _buscar_projetos_db(ProjetoOnetime, email, squad)
    inativos = _buscar_projetos_db(ProjetoInativo, email, squad)
    
    # Formata para ser compatível com o que atualizarCards espera (baseado no formato n8n legado se necessário, 
    # mas aqui adaptamos para simplificar)
    return jsonify({
        "ativos": [{"projetos": p} for p in ativos],
        "onetime": [{"projetos": p} for p in onetime],
        "inativos": [{"projetos": p} for p in inativos]
    })


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

                # Formatação de MRR
                mrr_val = float(m.fixo_mrr_atual or 0) if m else 0.0
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
            p_ativos = db.query(ProjetoAtivo).all()
            p_onetime = db.query(ProjetoOnetime).all()
            projetos_todos = p_ativos + p_onetime
            
            mrr_total = 0
            usd_rate = float(CurrencyService.get_usd_to_brl_rate())
            
            for p in projetos_todos:
                fee_p = float(p.fee or 0)
                if str(p.moeda).strip().upper() == "USD":
                    mrr_total += fee_p * usd_rate
                else:
                    mrr_total += fee_p
            
            active_clients = db.query(ProjetoAtivo).count()
            nps_avg = db.query(func.avg(OperacaoCheckin.csat_pontuacao)).filter(OperacaoCheckin.csat_pontuacao != None).scalar() or 0
            
            # 2. Ranking: Para LTV completo, precisamos de Ativos + Onetime + Inativos
            ranking = db.query(ProjetoAtivo).all() + db.query(ProjetoOnetime).all() + db.query(ProjetoInativo).all()
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

                projetos_cliente = (
                    db.query(ProjetoAtivo).filter(ProjetoAtivo.pipefy_id == cid).all() +
                    db.query(ProjetoOnetime).filter(ProjetoOnetime.pipefy_id == cid).all() +
                    db.query(ProjetoInativo).filter(ProjetoInativo.pipefy_id == cid).all()
                )
                cliente = projetos_cliente[0] if projetos_cliente else None
                
                if not cliente:
                    return redirect(url_for("hub_cs_cx"))
                
                # Senioridade Real (desde o primeiro projeto histórico com o mesmo nome)
                data_primeiro = db.query(func.min(ProjetoAtivo.data_de_inicio)).filter(ProjetoAtivo.nome == cliente.nome).scalar()
                # Verifica também nos inativos se houver
                data_primeiro_inativo = db.query(func.min(ProjetoInativo.data_de_inicio)).filter(ProjetoInativo.nome == cliente.nome).scalar()
                if data_primeiro_inativo and (not data_primeiro or data_primeiro_inativo < data_primeiro):
                    data_primeiro = data_primeiro_inativo
                
                cliente.tempo_de_casa_meses = calculate_meses_to(data_primeiro or cliente.data_de_inicio, today)
                
                # Agrega métricas da conta com conversão
                cliente.mrr_total = 0
                for p in projetos_cliente:
                    fee_p = float(p.fee or 0)
                    if str(p.moeda).strip().upper() == "USD":
                        cliente.mrr_total += fee_p * usd_rate
                    else:
                        cliente.mrr_total += fee_p

                # Cálculo Real de LTV Histórico por Semestre (Ativos + Inativos)
                projetos_inativos = db.query(ProjetoInativo).filter(ProjetoInativo.nome == cliente.nome).all()
                todos_historico = projetos_cliente + projetos_inativos
                
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)