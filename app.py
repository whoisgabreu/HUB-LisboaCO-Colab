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
from services.projeto_participacao_service import ProjetoParticipacaoService


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
        ProjetoParticipacaoService.sincronizar_remuneracao(dt.now().month, dt.now().year)
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
            
            # Se for Gerência ou Sócio via posição, concede acesso a quase tudo
            is_high_level = user_posicao in ["Gerência", "Sócio"]
            
            # Verifica se o cargo solicitado está na lista ou se é Gerência/Sócio
            if not is_high_level and not any(role.lower() == user_role.lower() for role in roles):
                return render_template("index.html", error="Acesso restrito.")
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
            if squad_usuario == "Gerência" or session.get("posicao") == "Gerência":
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

            projetos = db.query(ProjetoAtivo).all()
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
                        "role": investidor.funcao or investidor.posicao,
                        "senioridade": metrica.senioridade or investidor.senioridade or "",
                        "nivel": metrica.level or investidor.nivel or "",
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
                    "role": investidor.funcao or investidor.posicao,
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
            if squad == "Gerência" or session.get("posicao") == "Gerência":
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

            # Filtra posição Gerência
            if investidor.posicao and investidor.posicao.lower() == "gerência":
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
            posicoes = ["Operação", "Gerência", "Meio", "Sócio"]
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
                "ativo": u.ativo
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
def processar_remuneracao():
    """Endpoint para processar métricas do mês atual."""
    from datetime import datetime as dt
    try:
        calcular_metricas_mensais(dt.now().month, dt.now().year)
        ProjetoParticipacaoService.sincronizar_remuneracao(dt.now().month, dt.now().year)
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
    """Retorna investidores vinculados a um projeto."""
    try:
        with Session() as db:
            vinculos = db.query(InvestidorProjeto).filter_by(pipefy_id_projeto=pipefy_id).all()
            return jsonify([{
                "id": v.id,
                "email": v.email_investidor,
                "cientista": v.cientista,
                "active": v.active,
                "fee_contribuicao": float(v.fee_contribuicao or 0)
            } for v in vinculos])
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projetos/vincular", methods=["POST"])
@check_session
@check_access(["Gerência"])
def vincular_investidor():
    """Vincula um investidor a um projeto."""
    data = request.json
    email_investidor = data.get("email_investidor")
    pipefy_id = data.get("pipefy_id_projeto")
    cientista = data.get("cientista", False)
    
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
@check_access(["Gerência"])
def update_projeto_local(pipefy_id):
    """Atualiza dados do projeto e sincroniza vínculos."""
    data = request.json
    try:
        from decimal import Decimal
        with Session() as db:
            projeto = db.query(ProjetoAtivo).filter_by(pipefy_id=pipefy_id).first()
            is_onetime = False
            if not projeto:
                projeto = db.query(ProjetoOnetime).filter_by(pipefy_id=pipefy_id).first()
                is_onetime = True
            
            if not projeto:
                return jsonify({"error": "Projeto não encontrado."}), 404

            # Rastreamento de alterações para o histórico
            changes = {}
            fields_to_track = {
                "nome": "Nome",
                "fee": "Fee",
                "moeda": "Moeda",
                "squad_atribuida": "Squad",
                "produto_contratado": "Produto",
                "step": "Fase",
                "informacoes_gerais": "Informações Gerais",
                "ekyte_workspace": "Ekyte Workspace"
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
            if "fee" in data: projeto.fee = int(data["fee"])
            if "moeda" in data: projeto.moeda = data["moeda"]
            if "squad_atribuida" in data: projeto.squad_atribuida = data["squad_atribuida"]
            if "produto_contratado" in data: projeto.produto_contratado = data["produto_contratado"]
            if "step" in data: projeto.step = data["step"]
            if "informacoes_gerais" in data: projeto.informacoes_gerais = data["informacoes_gerais"]
            if "ekyte_workspace" in data: projeto.ekyte_workspace = data["ekyte_workspace"]
            
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
                
                if v:
                    # Atualiza existente
                    v.nome_projeto = data.get("nome", v.nome_projeto)
                    v.fee_projeto = Decimal(str(data.get("fee", v.fee_projeto) or 0))

                    v.cientista = cientista
                else:
                    # Cria novo
                    novo_v = InvestidorProjeto(
                        pipefy_id_projeto=pipefy_id,
                        email_investidor=email,
                        nome_projeto=data.get("nome", projeto.nome),
                        fee_projeto=Decimal(str(data.get("fee", projeto.fee) or 0)),
                        cientista=cientista,
                        active=True,
                        created_at=dt.now()
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
                        # base_date costuma ser date ou datetime
                        d_base = base_date if isinstance(base_date, date) else base_date.date() if hasattr(base_date, 'date') else None
                        if d_base:
                            delta = now.date() - d_base
                            days_without_churn = max(0, delta.days)
                
                # Mapeamento de Level para Senioridade de Mercado
                level_map = {
                    "L1": "Júnior", "L2": "Pleno", "L3": "Sênior", "L4": "Sênior", "L5": "Especialista"
                }
                raw_level = m.level if m else inv.nivel
                display_seniority = level_map.get(raw_level, raw_level)

                # Formatação de MRR para o front
                mrr_val = float(m.fixo_mrr_atual or 0) if m else 0.0
                mrr_formatted = f"R$ {mrr_val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

                ranking_list.append({
                    "id": inv.id,
                    "email": inv.email,
                    "name": inv.nome,
                    "role": inv.funcao or inv.posicao,
                    "level": display_seniority,
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


<<<<<<< HEAD
@app.route("/api/cs/metrics", methods=["GET"])
@check_session
def get_cs_metrics():
    try:
        from services.currency import CurrencyService
        from sqlalchemy import extract
        from datetime import datetime as dt
        
        now = dt.now()
        with Session() as db:
            # 1. MRR e Clientes Ativos
            projetos_ativos = db.query(ProjetoAtivo).all()
            clients_count = len(projetos_ativos)
            mrr_total = 0
            usd_rate = float(CurrencyService.get_usd_to_brl_rate())
            
            ltv_ranking = []
            
            for p in projetos_ativos:
                fee = float(p.fee or 0)
                m_code = str(p.moeda).strip().upper() if p.moeda else "BRL"
                converted_fee = fee * usd_rate if m_code == 'USD' else fee
                mrr_total += converted_fee
                
                # Cálculo simples de LTV: fee atual * meses de casa
                meses = 1
                if p.data_de_inicio:
                    delta = now.date() - p.data_de_inicio
                    meses = max(1, delta.days // 30)
                
                ltv_valor = converted_fee * meses
                ltv_ranking.append({"name": p.nome, "val": ltv_valor})
            
            # Ordenar Top 5 LTV
            ltv_ranking.sort(key=lambda x: x["val"], reverse=True)
            top_ltv = [{"name": x["name"], "val": f"R$ {x['val']/1000:.1f}k"} for x in ltv_ranking[:5]]

            # 2. Churn (Empresas inativadas no mês atual)
            churn_count = db.query(InvestidorProjeto).filter(
                InvestidorProjeto.active == False,
                extract('month', InvestidorProjeto.inactivated_at) == now.month,
                extract('year', InvestidorProjeto.inactivated_at) == now.year
            ).count()

            # 3. Health Score Médio (Baseado nas Flags das Metricas Mensais)
            from models import MetricaMensal
            metricas = db.query(MetricaMensal).filter(
                MetricaMensal.mes == now.month,
                MetricaMensal.ano == now.year
            ).all()
            
            avg_health = 80 # Default
            if metricas:
                greens = sum(1 for m in metricas if m.flag == 'GREEN')
                avg_health = int((greens / len(metricas)) * 100)

            # 4. Construção de Histórico Real (Empresas Únicas)
            from sqlalchemy import distinct, func, or_
            
            monthly_labels = ['Jan', 'Fev', 'Mar']
            monthly_active = []
            monthly_churn = []
            history_mrr_trends = [] # para o gráfico de LTV
            
            # Quarters: visão maior para o LTV
            quarter_labels = ['2025-Q3', '2025-Q4', '2026-Q1']
            quarter_ltv = []
            
            # Dados Mensais (Focados em Empresa Única) - Jan/Fev/Mar 2026
            for m in [1, 2, 3]:
                if m <= now.month:
                    # 1. Empresas Ativas (Snaphost)
                    # Contamos IDs únicos de projetos que existiam/existem vinculados a profissionais
                    if m == now.month:
                        active_count = len(projetos_ativos)
                    else:
                        # Para meses passados, estimamos via InvestidorProjeto
                        from datetime import date
                        import calendar
                        last_day = calendar.monthrange(2026, m)[1]
                        last_date = date(2026, m, last_day)
                        
                        active_count = db.query(distinct(InvestidorProjeto.pipefy_id_projeto)).filter(
                            InvestidorProjeto.created_at <= last_date,
                            or_(
                                InvestidorProjeto.active == True,
                                InvestidorProjeto.inactivated_at > last_date
                            )
                        ).count()
                    
                    # 2. Churn (Empresas Únicas Inativadas no mês m)
                    churn_unique = db.query(distinct(InvestidorProjeto.pipefy_id_projeto)).filter(
                        InvestidorProjeto.active == False,
                        extract('month', InvestidorProjeto.inactivated_at) == m,
                        extract('year', InvestidorProjeto.inactivated_at) == 2026
                    ).count()
                    
                    monthly_active.append(active_count)
                    monthly_churn.append(churn_unique)
                    
                    # MRR do mês para o gráfico de LTV (Ticket Médio)
                    if m == now.month:
                        m_mrr = mrr_total
                    else:
                        m_mrr = db.query(func.sum(MetricaMensal.fixo_mrr_atual)).filter(
                            MetricaMensal.mes == m, MetricaMensal.ano == 2026
                        ).scalar() or 0
                    
                    avg_ticket = float(m_mrr) / active_count if active_count > 0 else 0
                    history_mrr_trends.append(avg_ticket)

            # 5. Dados por Quarter (LTV de Longo Prazo)
            quarters_cfg = [
                (2025, [7, 8, 9], '2025-Q3'),
                (2025, [10, 11, 12], '2025-Q4'),
                (2026, [1, 2, 3], '2026-Q1')
            ]
            
            for q_ano, q_meses, q_label in quarters_cfg:
                if q_ano == 2026:
                    q_val = sum(history_mrr_trends) / len(history_mrr_trends) if history_mrr_trends else 0
                else:
                    # Cálculo robusto para 2025
                    mrr_q = db.query(func.avg(MetricaMensal.fixo_mrr_atual)).filter(
                        MetricaMensal.ano == q_ano, MetricaMensal.mes.in_(q_meses)
                    ).scalar() or 0
                    
                    from datetime import date
                    max_date = date(q_ano, q_meses[-1], 28)
                    count_q = db.query(func.count(distinct(ProjetoAtivo.pipefy_id))).filter(
                        ProjetoAtivo.data_de_inicio <= max_date
                    ).scalar() or 1
                    
                    q_val = float(mrr_q) / count_q if count_q > 0 else 0
                
                quarter_ltv.append(q_val)

            return jsonify({
                "mrr": mrr_total,
                "clients": clients_count,
                "churn_count": churn_count,
                "ltv_avg": mrr_total / clients_count if clients_count > 0 else 0,
                "top_ltv": top_ltv,
                "health_score": avg_health,
                "history": {
                    "monthly": {
                        "labels": monthly_labels[:len(monthly_active)],
                        "active": monthly_active,
                        "churn": monthly_churn
                    },
                    "quarterly": {
                        "labels": quarter_labels,
                        "ltv": quarter_ltv
                    }
                }
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


=======
>>>>>>> 4d6360c19ebc8f29b528a4d0513e24c63ba50bf9
@app.route("/cockpit", methods=["GET"])
@check_session
def cockpit():
    return render_template("cockpit.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)