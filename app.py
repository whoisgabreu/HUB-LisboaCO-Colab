from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from flask_apscheduler import APScheduler
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from collections import defaultdict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime as dt
import os
import json

from database import Session, engine, Base
from models import (
    Investidor, Auth, ProjetoAtivo, ProjetoOnetime, ProjetoInativo,
    MetricaMensal, InvestidorProjeto,
    OperacaoTarefa, OperacaoEntregaMensal, OperacaoPlanoMidia,
    OperacaoOtimizacao, OperacaoCheckin,
    MonthlyDelivery, OperacaoLinkUtil
)
from services.remuneracao import calcular_metricas_mensais
from services.delivery_engine import process_deliveries, process_all_deliveries_for_project
from services.delivery_service import DeliveryService
from services.operacao_service import OperacaoService

# Cria as tabelas caso não existam no banco
Base.metadata.create_all(engine)

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
            if not any(role.lower() == user_role.lower() for role in roles) and session.get("squad") != "Gerência":
                return render_template("index.html", error="Acesso restrito a Accounts e Gestores de Tráfego.")
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ─── HELPERS ────────────────────────────────────────────────────────────────

def recalculate_investor_mrr(db, email, mes, ano):
    """
    NÃO-OP: remuneração agora é baseada exclusivamente no fee_projeto.
    Entregas não influenciam o MRR armazenado.
    O recálculo real é feito pelo scheduler diário via calcular_metricas_mensais.
    """
    return 0


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
            if squad_usuario == "Gerência":
                projetos = db.query(model_class).all()
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

            projetos = db.query(ProjetoAtivo).all()
            mrr_total = 0
            usd_rate = None
            for p in projetos:
                fee = float(p.fee or 0)
                if p.moeda and p.moeda.upper() not in ['BRL', 'R$']:
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

                projetos_vinculados = [
                    {"id": v.pipefy_id_projeto, "nome": v.nome_projeto, "fee": float(v.fee_projeto or 0), "active": v.active}
                    for v in vinculos
                ]

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
                        "role": investidor.funcao,
                        "senioridade": metrica.senioridade or investidor.senioridade,
                        "nivel": metrica.level or investidor.nivel,
                        "fixed_fee": float(primeira_metrica.fixo_remuneracao_fixa or 0),
                    })

                # Inverte para que [-1] seja o mais recente (igual ao hub_remuneracao)
                rows.reverse()

                last_row = rows[-1] if rows else {}
                rem_min = float(primeira_metrica.fixo_remuneracao_minima or 0)
                rem_max = float(primeira_metrica.fixo_remuneracao_maxima or 0)
                total_brl = last_row.get("total_brl", 0)
                rem_atual = rem_min if total_brl < rem_min else (rem_max if total_brl > rem_max else total_brl)

                my_remuneracao = {
                    "name": investidor.nome,
                    "role": investidor.funcao,
                    "squad": investidor.squad,
                    "profile_picture": investidor.profile_picture,
                    "fixed_fee": float(primeira_metrica.fixo_remuneracao_fixa or 0),
                    "mrr": float(primeira_metrica.fixo_mrr_entrega or 0),
                    "mrrTotal": float(primeira_metrica.fixo_mrr_projeto_total or 0),
                    "mrrEsperado": float(primeira_metrica.fixo_mrr_esperado or 0),
                    "mrrTeto": float(primeira_metrica.fixo_mrr_teto or 0),
                    "rem_min": rem_min,
                    "rem_max": rem_max,
                    "rem_atual": round(rem_atual, 2),
                    "churn_rs": last_row.get("churn_rs", 0),
                    "clients_count": clients_count_user,
                    "projetos_total": len(projetos_vinculados),
                    "projetos_vinculados": json.dumps(projetos_vinculados),
                    "rows": rows,
                }
    except Exception as e:
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
            if squad == "Gerência":
                projetos_squad = db.query(ProjetoAtivo).all()
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
@check_access(["Gerência"])
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
            # Considera apenas projetos ativos ou inativados no mês corrente
            hoje = dt.now()
            mes_atual = hoje.month
            ano_atual = hoje.year

            from sqlalchemy import extract, or_, and_
            all_vinculos = db.query(InvestidorProjeto).filter(
                or_(
                    InvestidorProjeto.active == True,
                    and_(
                        InvestidorProjeto.active == False,
                        extract('month', InvestidorProjeto.inactivated_at) == mes_atual,
                        extract('year', InvestidorProjeto.inactivated_at) == ano_atual
                    )
                )
            ).all()

            projetos_map = {}
            for v in all_vinculos:
                if v.email_investidor not in projetos_map:
                    projetos_map[v.email_investidor] = []
                # Inclui ID, Nome e Fee para exibição detalhada
                projetos_map[v.email_investidor].append({
                    "id": v.pipefy_id_projeto,
                    "nome": v.nome_projeto,
                    "fee": float(v.fee_projeto or 0),
                    "active": v.active
                })


            # 2. Busca métricas mais recentes agrupadas por investidor
            metricas_raw = db.query(MetricaMensal, Investidor).join(
                Investidor, MetricaMensal.email_investidor == Investidor.email
            ).order_by(
                MetricaMensal.email_investidor,
                MetricaMensal.ano.desc(),
                MetricaMensal.mes.desc()
            ).all()

        # Agrupa histórico por investidor
        investidores_dict = {}
        for metrica, investidor in metricas_raw:
            email = metrica.email_investidor

            # Filtra squad Gerência
            if investidor.squad and investidor.squad.lower() == "gerência":
                continue

            if email not in investidores_dict:
                investidores_dict[email] = {
                    "id": f"inv_{email.replace('@', '_').replace('.', '_')}",
                    "name": investidor.nome,
                    "email": investidor.email,
                    "profile_picture": investidor.profile_picture,
                    "role": investidor.funcao,
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


# ─── OUTRAS PÁGINAS ──────────────────────────────────────────────────────────

@app.route("/hub-cs-cx", methods=["GET"])
@check_session
def hub_cs_cx():
    return render_template("hub-cs-cx.html")


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
    
    try:
        with Session() as db:
            meus_projetos = OperacaoService.get_projetos_operacao(db, email, squad)
            
    except SQLAlchemyError as e:
        print(f"Erro ao carregar operação: {e}")
        meus_projetos = []

    return render_template("operacao.html", projetos=meus_projetos)


@app.route("/criativa", methods=["GET"])
@check_session
@check_access(["Designer", "WebDesigner"])
def criativa():
    return render_template("criativa.html")


# ─── APIs OPERAÇÃO ───────────────────────────────────────────────────────────

@app.route("/api/operacao/tarefas/<int:pipefy_id>", methods=["GET"])
@check_session
@check_access(["Account", "Gestor de Tráfego"])
def get_tarefas(pipefy_id):
    tipo = request.args.get("tipo", "semanal")
    referencia = request.args.get("referencia")
    try:
        with Session() as db:
            query = db.query(OperacaoTarefa).filter_by(projeto_pipefy_id=pipefy_id, tipo=tipo)
            if referencia:
                query = query.filter_by(referencia=referencia)
            tarefas = query.all()
            return jsonify([{
                "id": t.id,
                "descricao": t.descricao,
                "concluida": t.concluida,
                "referencia": t.referencia
            } for t in tarefas])
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/tarefas", methods=["POST"])
@check_session
@check_access(["Account", "Gestor de Tráfego"])
def save_tarefa():
    data = request.json
    try:
        with Session() as db:
            if data.get("id"):
                tarefa = db.get(OperacaoTarefa, data["id"])
                if tarefa:
                    tarefa.concluida = data.get("concluida", tarefa.concluida)
                    tarefa.descricao = data.get("descricao", tarefa.descricao)
            else:
                tarefa = OperacaoTarefa(
                    projeto_pipefy_id=data["pipefy_id"],
                    tipo=data["tipo"],
                    descricao=data["descricao"],
                    referencia=data["referencia"],
                    ano=data["ano"],
                    concluida=False
                )
                db.add(tarefa)
            db.commit()
            
            # Trigger DeliveryService for relevant types based on task type (E4)
            email_sessao = session.get("email")
            if tarefa.tipo == 'quarter':
                DeliveryService.checkAndComplete(email_sessao, tarefa.projeto_pipefy_id, 'relatorio_account', dt.now().month, dt.now().year)
                DeliveryService.checkAndComplete(email_sessao, tarefa.projeto_pipefy_id, 'relatorio_gt', dt.now().month, dt.now().year)
                DeliveryService.checkAndComplete(email_sessao, tarefa.projeto_pipefy_id, 'forecasting', dt.now().month, dt.now().year)
            elif tarefa.tipo == 'semanal':
                DeliveryService.checkAndComplete(email_sessao, tarefa.projeto_pipefy_id, 'planner_monday', dt.now().month, dt.now().year)
                DeliveryService.checkAndComplete(email_sessao, tarefa.projeto_pipefy_id, 'config_conta', dt.now().month, dt.now().year)

            return jsonify({"status": "success", "id": tarefa.id})
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


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

@app.route("/api/operacao/monthly-deliveries/<int:pipefy_id>/<int:mes>/<int:ano>", methods=["GET"])
@check_session
@check_access(["Account", "Gestor de Tráfego"])
def get_monthly_deliveries(pipefy_id, mes, ano):
    """Retorna as entregas automáticas do mês para o usuário logado neste projeto."""
    email = session.get("email")
    try:
        with Session() as db:
            entregas = db.query(MonthlyDelivery).filter_by(
                email=email,
                client_id=pipefy_id,
                month=mes,
                year=ano,
            ).all()
            return jsonify([{
                "id": e.id,
                "role": e.role,
                "delivery_type": e.delivery_type,
                "status": e.status,
                "fee_snapshot": float(e.fee_snapshot or 0),
                "mrr_contribution": float(e.mrr_contribution or 0),
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            } for e in entregas])
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/entregas", methods=["POST"])
@check_session
def block_manual_entrega():
    """Marcação manual de entregas foi desabilitada. Entregas são 100% automáticas."""
    return jsonify({"error": "Marcação manual de entregas não é permitida. As entregas são geradas automaticamente pelo sistema."}), 403

@app.route("/api/remuneracao/processar")
@check_session
@check_access(["Admin", "Sócio", "Gerência"])
def processar_remuneracao():
    """Endpoint para processar métricas do mês atual."""
    from datetime import datetime as dt
    try:
        calcular_metricas_mensais(dt.now().month, dt.now().year)
        return jsonify({"status": "success", "message": "Métricas processadas."})
    except Exception as e:
        print(f"Erro ao processar remuneracao: {e}")
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
@check_access(["Gestor de Tráfego"])
def save_plano_midia():
    data = request.json
    email = session.get("email")
    print(f"DEBUG: save_plano_midia POST - Email: {email}, ID: {data.get('pipefy_id')}, Mes: {data.get('mes')}")
    try:
        with Session() as db:
            # Filtrar por email também para evitar conflitos de cargos
            plano = db.query(OperacaoPlanoMidia).filter_by(
                projeto_pipefy_id=data["pipefy_id"], 
                mes=data["mes"], 
                ano=data["ano"],
                investidor_email=email
            ).first()

            if not plano:
                print("DEBUG: Creating new plan record")
                plano = OperacaoPlanoMidia(
                    projeto_pipefy_id=data["pipefy_id"], mes=data["mes"], ano=data["ano"],
                    investidor_email=email, created_at=dt.now()
                )
                db.add(plano)
            else:
                print("DEBUG: Updating existing plan record")
            
            plano.dados_plano = data.get("dados_plano", {})
            plano.updated_at = dt.now()
            db.commit()

        # Trigger delivery_engine and DeliveryService (E4)
        DeliveryService.checkAndComplete(email, data["pipefy_id"], "plano_midia", data["mes"], data["ano"])
        res_engine = process_deliveries(email, data["pipefy_id"], data["mes"], data["ano"])
        print(f"DEBUG: Delivery engine result: {res_engine}")
        return jsonify({"status": "success", "engine": res_engine})
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/operacao/plano-midia/<int:pipefy_id>/<int:mes>/<int:ano>", methods=["GET"])
@check_session
@check_access(["Account", "Gestor de Tráfego"])
def get_plano_midia(pipefy_id, mes, ano):
    try:
        with Session() as db:
            # Primeiro tenta buscar o plano do próprio usuário
            plano = db.query(OperacaoPlanoMidia).filter_by(
                projeto_pipefy_id=pipefy_id, mes=mes, ano=ano,
                investidor_email=session.get("email")
            ).first()

            # Se não houver do usuário, tenta qualquer um do projeto para visualização/compartilhamento
            if not plano:
                plano = db.query(OperacaoPlanoMidia).filter_by(
                    projeto_pipefy_id=pipefy_id, mes=mes, ano=ano
                ).first()
            if plano:
                return jsonify({
                    "id": plano.id,
                    "dados_plano": plano.dados_plano,
                    "created_at": plano.created_at.isoformat() if plano.created_at else None
                })
            return jsonify(None)
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/operacao/otimizacao", methods=["POST"])
@check_session
@check_access(["Gestor de Tráfego"])
def save_otimizacao_api():
    data = request.json
    email = session.get("email")
    try:
        with Session() as db:
            nova = OperacaoOtimizacao(
                projeto_pipefy_id=data["pipefy_id"],
                investidor_email=email,
                tipo=data["tipo"],
                canal=data["canal"],
                data_otimizacao=dt.strptime(data["data"], "%Y-%m-%d"),
                detalhes=data["detalhes"],
                created_at=dt.now()
            )
            db.add(nova)
            db.commit()

        # Trigger delivery_engine and DeliveryService (E4)
        d = dt.strptime(data["data"], "%Y-%m-%d")
        DeliveryService.checkAndComplete(email, data["pipefy_id"], "otimizacao", d.month, d.year)
        process_deliveries(email, data["pipefy_id"], d.month, d.year)
        return jsonify({"status": "success"})
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/operacao/checkin", methods=["POST"])
@check_session
@check_access(["Account"])
def save_checkin():
    data = request.json
    email = session.get("email")
    try:
        with Session() as db:
            novo = OperacaoCheckin(
                projeto_pipefy_id=data["pipefy_id"],
                investidor_email=email,
                semana_ano=data["semana_ano"],
                compareceu=data["compareceu"],
                campanhas_ativas=data.get("campanhas_ativas", True),
                gap_comunicacao=data.get("gap_comunicacao", False),
                cliente_reclamou=data.get("cliente_reclamou", False),
                satisfeito=data.get("satisfeito", True),
                csat_pontuacao=data.get("csat"),
                observacoes=data.get("obs"),
                created_at=dt.now()
            )
            db.add(novo)
            db.commit()

        # Trigger delivery_engine and DeliveryService (E4)
        DeliveryService.checkAndComplete(email, data["pipefy_id"], "checkin", dt.now().month, dt.now().year)
        process_deliveries(email, data["pipefy_id"], dt.now().month, dt.now().year)
        return jsonify({"status": "success"})
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/operacao/checkins/<int:pipefy_id>", methods=["GET"])
@check_session
@check_access(["Account", "Gestor de Tráfego"])
def get_checkins(pipefy_id):
    try:
        with Session() as db:
            checkins = db.query(OperacaoCheckin).filter_by(projeto_pipefy_id=pipefy_id).order_by(OperacaoCheckin.created_at.desc()).all()
            return jsonify([{
                "semana": c.semana_ano,
                "compareceu": c.compareceu,
                "campanhas_ativas": c.campanhas_ativas,
                "gap_comunicacao": c.gap_comunicacao,
                "cliente_reclamou": c.cliente_reclamou,
                "satisfeito": c.satisfeito,
                "csat": c.csat_pontuacao,
                "obs": c.observacoes,
                "data": c.created_at.strftime("%d/%m/%Y") if c.created_at else ""
            } for c in checkins])
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


# ─── GET OTIMIZAÇÕES ─────────────────────────────────────────────────────────

@app.route("/api/operacao/otimizacoes/<int:pipefy_id>", methods=["GET"])
@check_session
@check_access(["Account", "Gestor de Tráfego"])
def get_otimizacoes(pipefy_id):
    """Lista todas as otimizações registradas para um projeto."""
    email = session.get("email")
    squad = session.get("squad")
    try:
        with Session() as db:
            query = db.query(OperacaoOtimizacao).filter_by(projeto_pipefy_id=pipefy_id)
            if squad != "Gerência":
                query = query.filter_by(investidor_email=email)
            otimizacoes = query.order_by(OperacaoOtimizacao.data_otimizacao.desc()).all()
            return jsonify([{
                "id": o.id,
                "tipo": o.tipo,
                "canal": o.canal,
                "data": o.data_otimizacao.strftime("%d/%m/%Y") if o.data_otimizacao else "",
                "detalhes": o.detalhes,
                "criado_em": o.created_at.strftime("%d/%m/%Y") if o.created_at else ""
            } for o in otimizacoes])
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


# ─── LINKS ÚTEIS ─────────────────────────────────────────────────────────────

@app.route("/api/operacao/links/<int:pipefy_id>", methods=["GET"])
@check_session
@check_access(["Account", "Gestor de Tráfego"])
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
@check_access(["Account", "Gestor de Tráfego"])
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
@check_access(["Account", "Gestor de Tráfego"])
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


@app.route("/cockpit", methods=["GET"])
@check_session
def cockpit():
    return render_template("cockpit.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)