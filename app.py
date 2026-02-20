from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash #hash de senha
import requests as req
import os
from collections import defaultdict

app = Flask(__name__)
app.secret_key = os.urandom(10).hex() 


def check_session(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "nome" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper

@app.route("/login", methods = ["GET","POST"])
def login():
    session.clear()
    if request.method == "POST":

        usuario = request.form["email"]
        senha = request.form["senha"]

        if usuario and senha:
            token = os.urandom(10).hex()

            response = req.get("https://n8n.v4lisboatech.com.br/webhook/check_login", params = {"email": usuario, "token": token})


            if response.status_code == 401:
                return render_template("login.html", error = "E-mail e/ou Senha incorreto(s).")

            print(usuario, senha, response.json())

            
            db_nome = response.json()[0].get("user").get("nome")
            db_email = response.json()[0].get("user").get("email")
            db_funcao = response.json()[0].get("user").get("funcao")
            db_senioridade = response.json()[0].get("user").get("senioridade")
            db_squad = response.json()[0].get("user").get("squad")
            db_senha = response.json()[0].get("user").get("senha")
            db_acesso = response.json()[0].get("user").get("nivel_acesso")
            db_ativo = response.json()[0].get("user").get("ativo")

            if db_ativo is not True:
                return render_template("login.html", error = "Login inativo. Fale com a Gerência.")

            if check_password_hash(db_senha, senha) == False:
                return render_template("login.html", error = "E-mail e/ou Senha incorreto(s).")


            session["nome"] = db_nome
            session["email"] = db_email
            session["token"] = token
            session["funcao"] = db_funcao
            session["senioridade"] = db_senioridade
            session["squad"] = db_squad
            session["nivel_acesso"] = db_acesso

            return redirect(url_for("home"))

    return render_template("login.html")

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/", methods = ["GET"])
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

@app.route("/hub-projetos", methods = ["GET"])
@check_session
def hub_projetos(): # Página transferida do primeiro Omni
    print("a")
    def agrupar_por_cliente(projetos_lista):
        """Agrupa projetos por nome do cliente, ordenados por id"""

        # ordena a lista pelo campo id
        projetos_ordenados = sorted(
            projetos_lista,
            key=lambda item: item.get('projetos', {}).get('id', 0)
        )

        clientes = defaultdict(list)

        for item in projetos_ordenados:
            projeto = item.get('projetos', {})
            cliente_nome = projeto.get('nome', 'Cliente Desconhecido')
            clientes[cliente_nome].append(projeto)

        return dict(clientes)

    def buscar_projetos(url, email):
        """Busca projetos com tratamento de erro"""
        try:
            response = req.get(url, headers={"x-api-key": session["token"]}, params={"email": email}, timeout=10)
            
            # Verifica se a resposta tem conteúdo
            if response.status_code == 200 and response.text.strip():
                try:
                    return response.json()
                except ValueError:
                    print(f"Erro ao parsear JSON de {url}")
                    return []
            else:
                print(f"Resposta vazia ou erro de {url}: status {response.status_code}")
                return []
                
        except req.exceptions.RequestException as e:
            print(f"Erro na requisição para {url}: {e}")
            return []

    # Buscar projetos com tratamento de erro
    

    resp = req.get(f"https://n8n.v4lisboatech.com.br/webhook/squads?email={session["email"]}", headers= {"x-api-key": session["token"]})
    squads = [x["projetos"]["nome"] for x in resp.json()]

    ativos_data = buscar_projetos(
        "https://n8n.v4lisboatech.com.br/webhook/list_projetos",
        session["email"]
    )
    ativos = agrupar_por_cliente(ativos_data) if ativos_data else {}

    onetime_data = buscar_projetos(
        "https://n8n.v4lisboatech.com.br/webhook/list_projetos_onetime",
        session["email"]
    )
    onetime = agrupar_por_cliente(onetime_data) if onetime_data else {}

    inativos_data = buscar_projetos(
        "https://n8n.v4lisboatech.com.br/webhook/list_projetos_inativos",
        session["email"]
    )
    inativos = agrupar_por_cliente(inativos_data) if inativos_data else {}

    return render_template("hub-projetos.html", 
                         clientes_ativos = ativos, 
                         clientes_onetime = onetime, 
                         clientes_inativos = inativos,
                         squads = squads)

@app.route("/hub-remuneracao", methods = ["GET"])
@check_session
def hub_remuneracao():

    url = "https://n8n.v4lisboatech.com.br/webhook/remuneracao"

    response = req.get(url, headers={"x-api-key": session["token"]}, timeout=10)

    mock_investors = [
        {
            "id": "inv_1",
            "name": "Gabriel Lisboa",
            "role": "Sócio Diretor",
            "squad": "Estratégia",
            "step": "Potencializar",
            "clients_count": 12,
            "fixed_fee": 5000.00,
            "mrr": 45000.00,
            "roi": 0.85,
            "rows": [
                {"month_year": "01/2026", "mrr": 42000.0, "churn": 0.02, "variable_brl": 1200.0, "total_brl": 6200.0},
                {"month_year": "02/2026", "mrr": 45000.0, "churn": 0.0, "variable_brl": 1500.0, "total_brl": 6500.0}
            ]
        },
        {
            "id": "inv_2",
            "name": "Mariana Silva",
            "role": "Gestora de Growth",
            "squad": "Squad Alpha",
            "step": "Executar",
            "clients_count": 8,
            "fixed_fee": 3500.00,
            "mrr": 28000.00,
            "roi": 0.72,
            "rows": [
                {"month_year": "01/2026", "mrr": 25000.0, "churn": 0.05, "variable_brl": 800.0, "total_brl": 4300.0},
                {"month_year": "02/2026", "mrr": 28000.0, "churn": 0.01, "variable_brl": 950.0, "total_brl": 4450.0}
            ]
        },
        {
            "id": "inv_3",
            "name": "Ricardo Gomes",
            "role": "Analista Sênior",
            "squad": "Squad Beta",
            "step": "Saber",
            "clients_count": 5,
            "fixed_fee": 2800.00,
            "mrr": 15000.00,
            "roi": 0.60,
            "rows": [
                {"month_year": "02/2026", "mrr": 15000.0, "churn": 0.0, "variable_brl": 500.0, "total_brl": 3300.0}
            ]
        }
    ]

    try:
        mock_investors = response.json()

        # 🔥 FILTRO AQUI — remove squad "Gerência"
        mock_investors = [
            inv for inv in mock_investors
            if inv.get("squad", "").lower() != "gerência"
        ]

        squads = sorted(list(set(inv["squad"] for inv in mock_investors)))
        roles = sorted(list(set(inv["role"] for inv in mock_investors)))
        
    except:
        mock_investors = []
        squads = []
        roles = []
    return render_template("hub-remuneracao.html", 
                        investors=mock_investors, 
                        squads=squads, 
                        roles=roles)
        # return render_template("hub-remuneracao.html")

@app.route("/hub-cs-cx", methods = ["GET"])
@check_session
def hub_cs_cx():
    return render_template("hub-cs-cx.html")

@app.route("/painel-atribuicao", methods = ["GET"])
@check_session
def painel_atribuicao():
    return render_template("painel-atribuicao.html")

@app.route("/painel-ranking", methods = ["GET"])
@check_session
def painel_ranking():
    return render_template("painel-ranking.html")

@app.route("/vendas", methods = ["GET"])
@check_session
def vendas():
    return render_template("vendas.html")

@app.route("/cockpit", methods = ["GET"])
@check_session
def cockpit():
    return render_template("cockpit.html")

if __name__ == "__main__":
    app.run(host = "0.0.0.0", port=5000, debug = True)