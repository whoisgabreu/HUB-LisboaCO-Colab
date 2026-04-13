from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from .models import ProjetoAtivo, ProjetoOnetime, ProjetoInativo
from django.db.models import Q

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
    """Agrupa projetos por nome do cliente, ordenados por id."""
    projetos_ordenados = sorted(projetos_lista, key=lambda x: x.get("id", 0))
    clientes = defaultdict(list)
    for projeto in projetos_ordenados:
        cliente_nome = projeto.get("nome", "Cliente Desconhecido")
        clientes[cliente_nome].append(projeto)
    return dict(clientes)

def _buscar_projetos_db(model_class, squad_usuario, user_posicao):
    """Busca projetos no banco respeitando as regras de acesso."""
    if squad_usuario == "Gerência" or user_posicao == "Gerência":
        projetos = model_class.objects.all()
    else:
        projetos = model_class.objects.filter(squad_atribuida=squad_usuario)
    return [_projeto_to_dict(p) for p in projetos]

@login_required
def hub_projetos(request):
    squad = request.user.squad or ""
    posicao = request.user.posicao or ""
    
    # Busca squads disponíveis para o usuário
    if squad == "Gerência" or posicao == "Gerência":
        projetos_squad = ProjetoAtivo.objects.all()
    else:
        projetos_squad = ProjetoAtivo.objects.filter(squad_atribuida=squad)
    
    squads = sorted(list(set(p.squad_atribuida for p in projetos_squad if p.squad_atribuida)))

    ativos_data = _buscar_projetos_db(ProjetoAtivo, squad, posicao)
    ativos = _agrupar_por_cliente(ativos_data)

    onetime_data = _buscar_projetos_db(ProjetoOnetime, squad, posicao)
    onetime = _agrupar_por_cliente(onetime_data)

    inativos_data = _buscar_projetos_db(ProjetoInativo, squad, posicao)
    inativos = _agrupar_por_cliente(inativos_data)

    return render(request, "hub-projetos.html", {
        "clientes_ativos": ativos,
        "clientes_onetime": onetime,
        "clientes_inativos": inativos,
        "squads": squads
    })
