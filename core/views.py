from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from datetime import datetime as dt
import json
from decimal import Decimal
from projetos.models import ProjetoAtivo, InvestidorProjeto
from remuneracao.models import MetricaMensal
from services.currency import CurrencyService
from django.core.serializers.json import DjangoJSONEncoder

@login_required
def home(request):
    try:
        clients_count = ProjetoAtivo.objects.count()
        investors_count = request.user.__class__.objects.count()
        squads_count = ProjetoAtivo.objects.exclude(squad_atribuida__exact='').exclude(squad_atribuida__isnull=True).values('squad_atribuida').distinct().count()

        projetos = ProjetoAtivo.objects.all()
        mrr_total = Decimal("0.0")
        usd_rate = None
        for p in projetos:
            fee = Decimal(str(p.fee or 0))
            m_code = str(p.moeda).strip().upper() if p.moeda else "BRL"
            if m_code == 'USD':
                if usd_rate is None:
                    usd_rate = CurrencyService.get_usd_to_brl_rate()
                mrr_total += fee * usd_rate
            else:
                mrr_total += fee

        operational_data = {
            "mrr": float(mrr_total),
            "clients": clients_count,
            "investors": investors_count,
            "squads": squads_count
        }
    except Exception as e:
        print(f"Erro ao carregar dados operacionais: {e}")
        operational_data = {"mrr": 0, "clients": 0, "investors": 0, "squads": 0}

    # Métricas de remuneração do usuário logado
    my_remuneracao = None
    try:
        user_email = request.user.email
        # Busca todas as métricas do usuário, ordenadas por mais recente
        metricas_raw = MetricaMensal.objects.filter(email_investidor=user_email).order_by('-ano', '-mes')

        if metricas_raw.exists():
            hoje = dt.now()
            mes_atual = hoje.month
            ano_atual = hoje.year

            # Projetos vinculados
            vinculos = InvestidorProjeto.objects.filter(
                Q(email_investidor=user_email) & 
                (Q(active=True) | Q(active=False, inactivated_at__month=mes_atual, inactivated_at__year=ano_atual))
            )

            projetos_vinculados = [
                {"id": v.pipefy_id_projeto, "nome": v.nome_projeto, "fee": float(v.fee_projeto or 0), "active": v.active}
                for v in vinculos
            ]

            clients_count_user = InvestidorProjeto.objects.filter(email_investidor=user_email, active=True).count()
            primeira_metrica = metricas_raw[0]

            rows = []
            for metrica in metricas_raw:
                rows.append({
                    "month_year": f"{metrica.mes:02d}/{metrica.ano}",
                    "mrr": float(metrica.fixo_mrr_entrega or 0),
                    "mrrTotal": float(metrica.fixo_mrr_projeto_total or 0),
                    "churn": float(metrica.calc_churn_real_percentual or 0),
                    "churn_rs": float(metrica.fixo_churn_atual or 0),
                    "variable_brl": float(metrica.calc_variavel_total or 0),
                    "total_brl": float(max(metrica.calc_remuneracao_total or 0, metrica.fixo_remuneracao_minima or 0)),
                    "rem_min": float(metrica.fixo_remuneracao_minima or 0),
                    "rem_max": float(metrica.fixo_remuneracao_maxima or 0),
                    "yellow_streak": metrica.yellow_streak or 0,
                    "green_streak": metrica.green_streak or 0,
                    "motivo_flag": metrica.motivo_flag or "",
                    "role": metrica.cargo or request.user.funcao or request.user.posicao,
                    "senioridade": metrica.senioridade or request.user.senioridade or "",
                    "nivel": metrica.level or request.user.nivel or "",
                    "fixed_fee": float(primeira_metrica.fixo_remuneracao_fixa or 0),
                })

            rows.reverse()
            last_row = rows[-1] if rows else {}
            rem_min = float(primeira_metrica.fixo_remuneracao_minima or 0)
            rem_max = float(primeira_metrica.fixo_remuneracao_maxima or 0)
            total_brl = last_row.get("total_brl", 0)
            rem_atual = rem_min if total_brl < rem_min else (rem_max if total_brl > rem_max else total_brl)

            my_remuneracao = {
                "name": request.user.nome,
                "role": request.user.funcao or request.user.posicao,
                "squad": request.user.squad,
                "profile_picture": request.user.profile_picture,
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
                "projetos_vinculados": json.dumps(projetos_vinculados, cls=DjangoJSONEncoder),
                "rows": rows,
            }
    except Exception as e:
        print(f"Erro ao carregar remuneração do usuário: {e}")
        my_remuneracao = None

    return render(request, "index.html", {
        "operational_data": operational_data, 
        "operational_data_json": json.dumps(operational_data, cls=DjangoJSONEncoder),
        "my_remuneracao": my_remuneracao,
        "my_remu_json": json.dumps(my_remuneracao, cls=DjangoJSONEncoder) if my_remuneracao else "{}"
    })

@login_required
def painel_atribuicao(request):
    return render(request, "painel-atribuicao.html")

@login_required
def painel_ranking(request):
    return render(request, "painel-ranking.html")

@login_required
def vendas(request):
    return render(request, "vendas.html")

@login_required
def cockpit(request):
    return render(request, "cockpit.html")
