from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Q, Sum, Avg
from datetime import date
from .models import (
    OperacaoTarefa, OperacaoCheckin, OperacaoPlanoMidia,
    OperacaoOtimizacao, OperacaoLinkUtil, MonthlyDelivery
)
from projetos.models import ProjetoAtivo
from core.decorators import check_access
from services.operacao_service import OperacaoService
from services.delivery_engine import process_deliveries

@login_required
@check_access(["Account", "Gestor de Tráfego"])
def operacao(request):
    email = request.user.email
    squad = request.user.squad
    
    try:
        meus_projetos = OperacaoService.get_projetos_operacao(email, squad)
    except Exception as e:
        print(f"Erro ao carregar operação: {e}")
        meus_projetos = []

    return render(request, "operacao.html", {"projetos": meus_projetos})

# API Endpoints para a tela de Operação

@login_required
def api_get_tarefas(request, pipefy_id):
    tarefas = OperacaoTarefa.objects.filter(projeto_pipefy_id=pipefy_id).order_by('-ano', '-referencia')
    return JsonResponse([{
        "id": t.id,
        "tipo": t.tipo,
        "descricao": t.descricao,
        "concluida": t.concluida,
        "referencia": t.referencia
    } for t in tarefas], safe=False)

@login_required
def api_toggle_tarefa(request, tarefa_id):
    if request.method == "POST":
        try:
            tarefa = OperacaoTarefa.objects.get(id=tarefa_id)
            tarefa.concluida = not tarefa.concluida
            tarefa.save()
            
            # Ao alterar tarefa, processa entregas automáticas
            from datetime import datetime
            now = datetime.now()
            process_deliveries(request.user.email, tarefa.projeto_pipefy_id, now.month, now.year)
            
            return JsonResponse({"status": "success", "concluida": tarefa.concluida})
        except OperacaoTarefa.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Tarefa não encontrada"}, status=404)
    return JsonResponse({"status": "error", "message": "Método não permitido"}, status=405)

@login_required
def api_get_links(request, pipefy_id):
    links = OperacaoLinkUtil.objects.filter(projeto_pipefy_id=pipefy_id).order_by('-created_at')
    return JsonResponse([{
        "id": l.id,
        "titulo": l.titulo,
        "url": l.url,
        "descricao": l.descricao,
        "icone": l.icone
    } for l in links], safe=False)

@login_required
def criativa(request):
    """Tela de Gestão Criativa."""
    return render(request, "criativa.html")

@login_required
def hub_cs_cx(request):
    """Tela de Hub CS/CX."""
    view = request.GET.get("view", "dashboard")
    client_id = request.GET.get("client")
    
    # 1. KPIs Gerais
    active_clients = ProjetoAtivo.objects.count()
    mrr_total = ProjetoAtivo.objects.aggregate(Sum('fee'))['fee__sum'] or 0
    nps_avg = OperacaoCheckin.objects.filter(csat_pontuacao__isnull=False).aggregate(Avg('csat_pontuacao'))['csat_pontuacao__avg'] or 0
    
    # 2. Dados para o Ranking
    ranking_raw = ProjetoAtivo.objects.all().order_by('data_de_inicio')
    today = date.today()
    
    ranking = []
    for p in ranking_raw:
        # Tempo de casa
        if p.data_de_inicio:
            diff = today - p.data_de_inicio
            meses = max(1, diff.days // 30)
        else:
            meses = 0
            
        ranking.append({
            "pipefy_id": p.pipefy_id,
            "nome": p.nome,
            "produto_contratado": p.produto_contratado,
            "fee": float(p.fee or 0),
            "ltv_real": float(p.fee or 0) * meses,
            "health_score": 75 + (p.pipefy_id % 25), # Mock logic match
            "tempo_de_casa_meses_ranking": meses
        })

    if view == "detail" and client_id:
        try:
            cid = int(client_id)
            cliente = ProjetoAtivo.objects.get(pipefy_id=cid)
            
            # Dados extras para detalhes
            diff = today - (cliente.data_de_inicio or today)
            meses = max(1, diff.days // 30)
            
            cliente_data = {
                "pipefy_id": cliente.pipefy_id,
                "nome": cliente.nome,
                "produto_contratado": cliente.produto_contratado,
                "mrr_total": float(cliente.fee or 0),
                "ltv_total": float(cliente.fee or 0) * meses,
                "tempo_de_casa_meses": meses,
                "data_de_inicio": cliente.data_de_inicio,
                "squad_atribuida": cliente.squad_atribuida,
                "projetos_ativos": [cliente] # Por enquanto o próprio
            }
            
            return render(request, "cs_client_detail.html", {
                "cliente": cliente_data,
                "nps_valor": 9,
                "nps_data": "Semana Atual",
                "labels_ltv": ["Out", "Nov", "Dez", "Jan", "Fev", "Mar"],
                "dados_ltv": [1000, 2000, 3000, 4000, 5000, 6000],
                "labels_health": ["S1", "S2", "S3", "S4"],
                "dados_health": [80, 85, 82, 90],
                "equipe": [] # TODO: Fetch real team
            })
        except:
            return redirect("hub_cs_cx")
            
    return render(request, "cs_dashboard.html", {
        "active_clients": active_clients,
        "mrr_total": mrr_total,
        "nps_avg": nps_avg,
        "ranking": ranking
    })
