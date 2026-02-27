from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from flask_apscheduler import APScheduler
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from collections import defaultdict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import os
import json

from database import Session, engine, Base
from models import Investidor, Auth, ProjetoAtivo, ProjetoOnetime, ProjetoInativo, MetricaMensal, InvestidorProjeto, OperacaoTarefa, OperacaoEntregaMensal
from services.remuneracao import calcular_metricas_mensais

# Cria as tabelas caso não existam no banco
Base.metadata.create_all(engine)

app = Flask(__name__)
app.secret_key = os.urandom(10).hex()

# Configuração do Scheduler
scheduler = APScheduler()

def job_recalcular_remuneracao():
    """Tarefa agendada para rodar diariamente."""
    print(f"[{datetime.now()}] Iniciando recalculo automatico de remuneracao...")
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
    """Recalcula o MRR total do investidor somando as entregas de todos os seus projetos."""
    entregas = db.query(OperacaoEntregaMensal).filter_by(
        investidor_email=email, mes=mes, ano=ano
    ).all()
    
    total_mrr = sum(float(e.valor_contribuicao_mrr or 0) for e in entregas)
    
    metrica = db.query(MetricaMensal).filter_by(
        email_investidor=email, mes=mes, ano=ano
    ).first()
    
    if metrica:
        metrica.fixo_mrr_atual = total_mrr
        db.commit()
    return total_mrr


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
                        auth_entry = Auth(email=user.email, token=token)
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

                    return redirect(url_for("home"))

            except SQLAlchemyError as e:
                print(f"Erro de banco no login: {e}")
                return render_template("login.html", error="Erro ao conectar ao banco de dados.")

    return render_template("login.html")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ─── PÁGINAS ─────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
@check_session
def home():
    return render_template("index.html")


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


@app.route("/hub-remuneracao", methods=["GET"])
@check_session
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
            all_vinculos = db.query(InvestidorProjeto).all()
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
                    "role": investidor.funcao,
                    "squad": investidor.squad,
                    "senioridade": metrica.senioridade or investidor.senioridade,
                    "nivel": metrica.level or investidor.nivel,
                    "step": metrica.level,
                    "clients_count": clients_map.get(email, 0),
                    "fixed_fee": float(metrica.fixo_remuneracao_fixa or 0),
                    "projetos_vinculados": json.dumps(projetos_map.get(email, [])),
                    "mrr": float(metrica.fixo_mrr_atual or 0),
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
                "mrr": float(metrica.fixo_mrr_atual or 0),
                "mrrTotal": float(metrica.fixo_mrr_projeto_total or 0),
                "churn": float(metrica.calc_churn_real_percentual or 0),
                "churn_rs": float(metrica.fixo_churn_atual or 0),
                "variable_brl": float(metrica.calc_variavel_total or 0),
                "total_brl": float(metrica.calc_remuneracao_total or 0),
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
            # Busca projetos vinculados ao investidor
            if squad == "Gerência":
                projetos = db.query(ProjetoAtivo).all()
            else:
                projetos = db.query(ProjetoAtivo).join(
                    InvestidorProjeto, ProjetoAtivo.pipefy_id == InvestidorProjeto.pipefy_id_projeto
                ).filter(
                    InvestidorProjeto.email_investidor == email,
                    InvestidorProjeto.active == True
                ).all()
            
            meus_projetos = [_projeto_to_dict(p) for p in projetos]
            
    except SQLAlchemyError as e:
        print(f"Erro ao carregar operação: {e}")
        meus_projetos = []

    return render_template("operacao.html", projetos=meus_projetos)


# ─── APIs OPERAÇÃO ───────────────────────────────────────────────────────────

@app.route("/api/operacao/tarefas/<int:pipefy_id>", methods=["GET"])
@check_session
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
            return jsonify({"status": "success", "id": tarefa.id})
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/operacao/entregas/<int:pipefy_id>/<int:mes>/<int:ano>", methods=["GET"])
@check_session
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

@app.route("/api/operacao/entregas", methods=["POST"])
@check_session
def save_entregas():
    data = request.json
    email = session.get("email")
    pipefy_id = data["pipefy_id"]
    mes = data["mes"]
    ano = data["ano"]
    
    try:
        with Session() as db:
            # Busca o fee original do projeto
            projeto = db.get(ProjetoAtivo, pipefy_id)
            fee = float(projeto.fee or 0) if projeto else 0

            entrega = db.query(OperacaoEntregaMensal).filter_by(
                investidor_email=email, projeto_pipefy_id=pipefy_id, mes=mes, ano=ano
            ).first()
            
            if not entrega:
                entrega = OperacaoEntregaMensal(
                    investidor_email=email, projeto_pipefy_id=pipefy_id, mes=mes, ano=ano,
                    valor_fee_original=fee
                )
                db.add(entrega)
            
            # Atualiza flags de entrega
            for i in range(1, 5):
                key = f"entrega_{i}"
                if key in data:
                    setattr(entrega, key, data[key])
            
            # Calcula percentual: cada check = 0.25
            count = sum([1 for i in range(1, 5) if getattr(entrega, f"entrega_{i}")])
            entrega.percentual_calculado = count * 0.25
            entrega.valor_contribuicao_mrr = float(entrega.percentual_calculado) * fee
            
            # Sincroniza o fee_contribuicao na tabela investidores_projetos para todos os investidores do projeto
            vinculos = db.query(InvestidorProjeto).filter_by(pipefy_id_projeto=pipefy_id).all()
            for v in vinculos:
                v.fee_contribuicao = entrega.valor_contribuicao_mrr
            
            db.commit()
            
            # Gatilho para recálculo do MRR total do investidor no mês
            novo_mrr = recalculate_investor_mrr(db, email, mes, ano)
            
            return jsonify({
                "status": "success", 
                "percentual": float(entrega.percentual_calculado),
                "valor_mrr_projeto": float(entrega.valor_contribuicao_mrr),
                "mrr_total_atualizado": novo_mrr
            })
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/cockpit", methods=["GET"])
@check_session
def cockpit():
    return render_template("cockpit.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)