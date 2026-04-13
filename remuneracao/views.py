from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import connection, transaction
from django.db.models import Count, Q, Sum
from datetime import datetime as dt
import json
from django.core.serializers.json import DjangoJSONEncoder
from .models import MetricaMensal, RemuneracaoCargo
from users.models import Investidor
from projetos.models import InvestidorProjeto
from core.decorators import check_access
from services.remuneracao import calcular_metricas_mensais
from services.projeto_participacao_service import ProjetoParticipacaoService

@login_required
@check_access(["Gerência"])
def hub_remuneracao(request):
    try:
        # 1. Busca contagem de clientes por investidor
        client_counts = InvestidorProjeto.objects.filter(active=True).values('email_investidor').annotate(total=Count('pipefy_id_projeto'))
        clients_map = {item['email_investidor']: item['total'] for item in client_counts}

        # 2. Busca projetos vinculados por investidor
        hoje = dt.now()
        mes_atual = hoje.month
        ano_atual = hoje.year

        all_vinculos = InvestidorProjeto.objects.filter(
            Q(active=True) | 
            Q(active=False, inactivated_at__month=mes_atual, inactivated_at__year=ano_atual)
        )

        projetos_map = {}
        for v in all_vinculos:
            if v.email_investidor not in projetos_map:
                projetos_map[v.email_investidor] = []
            projetos_map[v.email_investidor].append({
                "id": v.pipefy_id_projeto,
                "nome": v.nome_projeto,
                "fee": float(v.fee_projeto or 0),
                "active": v.active
            })

        # 3. Busca métricas mais recentes agrupadas por investidor
        metricas_raw = MetricaMensal.objects.all().order_by('email_investidor', '-ano', '-mes')
        
        # Agrupa histórico por investidor
        investidores_dict = {}
        for metrica in metricas_raw:
            email = metrica.email_investidor
            
            # Precisamos do Investidor para pegar nome/squad/etc.
            # No Flask era um join. Aqui podemos otimizar ou buscar individualmente.
            # Para manter performance, vamos buscar todos os investidores uma vez.
            pass

        # Vamos refazer o join de forma eficiente
        users_info = {u.email: u for u in Investidor.objects.all()}

        for metrica in metricas_raw:
            email = metrica.email_investidor
            user = users_info.get(email)
            if not user: continue

            # Filtra posição Gerência
            if user.posicao and user.posicao.lower() == "gerência":
                continue

            if email not in investidores_dict:
                investidores_dict[email] = {
                    "id": f"inv_{email.replace('@', '_').replace('.', '_')}",
                    "name": user.nome,
                    "email": user.email,
                    "profile_picture": user.profile_picture,
                    "role": user.funcao or user.posicao,
                    "squad": user.squad,
                    "senioridade": metrica.senioridade or user.senioridade,
                    "nivel": metrica.level or user.nivel,
                    "step": metrica.level,
                    "clients_count": clients_map.get(email, 0),
                    "fixed_fee": float(metrica.fixo_remuneracao_fixa or 0),
                    "projetos_vinculados": json.dumps(projetos_map.get(email, []), cls=DjangoJSONEncoder),
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

        for email in investidores_dict:
            investidores_dict[email]["rows"].reverse()

        mock_investors = list(investidores_dict.values())
        squads = sorted(list(set(inv["squad"] for inv in mock_investors if inv["squad"])))
        roles = sorted(list(set(inv["role"] for inv in mock_investors if inv["role"])))

        return render(request, "hub-remuneracao.html", {
            "investors": mock_investors,
            "squads": squads,
            "roles": roles
        })
    except Exception as e:
        print(f"Erro ao carregar remuneração: {e}")
        return render(request, "hub-remuneracao.html", {
            "investors": [],
            "squads": [],
            "roles": []
        })

@login_required
@check_access(["Gerência"])
def api_processar_remuneracao(request):
    """Endpoint para disparar o cálculo manual de remuneração."""
    if request.method == "POST":
        try:
            hoje = dt.now()
            # 1. Calcula métricas core
            calcular_metricas_mensais(hoje.month, hoje.year)
            # 2. Sincroniza participação de projetos (histórico)
            ProjetoParticipacaoService.sincronizar_remuneracao(hoje.month, hoje.year)
            
            return JsonResponse({"status": "success", "message": "Remuneração processada com sucesso."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "error", "message": "Método não permitido."}, status=405)
