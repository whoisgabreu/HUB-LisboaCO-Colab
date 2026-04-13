from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import os
import secrets
from django.conf import settings
from .models import Auth, Investidor
from remuneracao.models import RemuneracaoCargo
from django.db.models import Q

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        senha = request.POST.get("senha")

        user = authenticate(request, username=email, password=senha)
        if user is not None:
            if not user.ativo:
                return render(request, "login.html", {"error": "Login inativo. Fale com a Gerência."})
            
            login(request, user)
            
            # Gera token e faz UPSERT na tabela auth (compatibilidade legada)
            token = secrets.token_hex(10)
            auth_entry, created = Auth.objects.get_or_create(email=user.email)
            auth_entry.token = token
            auth_entry.save()
            
            # Popula sessão explicitamente se os templates ainda usarem session.xxx
            # Mas o ideal é que usem request.user.xxx ou o context_processor do Django
            request.session["token"] = token
            
            return redirect("home")
        else:
            return render(request, "login.html", {"error": "E-mail e/ou Senha incorreto(s)."})

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
@csrf_exempt
def alterar_senha(request):
    if request.method == "POST":
        senha_atual = request.POST.get("senha_atual")
        nova_senha = request.POST.get("nova_senha")
        confirmar_senha = request.POST.get("confirmar_senha")

        if not senha_atual or not nova_senha or not confirmar_senha:
            return JsonResponse({"error": "Preencha todos os campos"}, status=400)

        if nova_senha != confirmar_senha:
            return JsonResponse({"error": "As senhas não coincidem"}, status=400)

        user = request.user
        if not user.check_password(senha_atual):
            return JsonResponse({"error": "Senha atual incorreta"}, status=400)

        user.set_password(nova_senha)
        user.save()
        update_session_auth_hash(request, user)
        return JsonResponse({"message": "Senha alterada com sucesso"})

    return JsonResponse({"error": "Método não permitido"}, status=405)

@login_required
def upload_profile_picture(request):
    if request.method == "POST" and request.FILES.get("foto"):
        arquivo = request.FILES["foto"]
        ext = os.path.splitext(arquivo.name)[1]
        nome_arquivo = f"{request.user.email}.png"
        caminho = os.path.join(settings.MEDIA_ROOT, nome_arquivo)
        
        with open(caminho, 'wb+') as destination:
            for chunk in arquivo.chunks():
                destination.write(chunk)
        
        user = request.user
        user.profile_picture = nome_arquivo
        user.save()

        return JsonResponse({
            "mensagem": "Foto salva com sucesso",
            "arquivo": nome_arquivo
        })

    return JsonResponse({"erro": "Nenhum arquivo enviado"}, status=400)
@login_required
def gerenciar_usuarios(request):
    if request.user.nivel_acesso != "Admin":
        return redirect("home")
    
    try:
        cargos = RemuneracaoCargo.objects.values_list('fixo_cargo', flat=True).distinct()
        senioridades = RemuneracaoCargo.objects.values_list('fixo_senioridade', flat=True).distinct()
        niveis = RemuneracaoCargo.objects.values_list('fixo_level', flat=True).distinct()
        
        posicoes = ["Operação", "Gerência", "Meio", "Sócio"]
        squads_db = Investidor.objects.exclude(squad__isnull=True).values_list('squad', flat=True).distinct()
        squads = sorted(list(set(list(squads_db) + ["Gerência", "Strike Force", "Shark", "Tigers"])))

        return render(request, "gerenciar-usuarios.html", {
            "options": {
                "cargos": sorted(list(cargos)),
                "senioridades": sorted(list(senioridades)),
                "niveis": sorted(list(niveis)),
                "posicoes": posicoes,
                "squads": squads
            }
        })
    except Exception as e:
        print(f"Erro ao carregar gerenciar usuários: {e}")
        return redirect("home")

@login_required
def api_get_usuarios(request):
    if request.user.nivel_acesso != "Admin":
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    users = Investidor.objects.all().order_by('nome')
    return JsonResponse([{
        "nome": u.nome,
        "email": u.email,
        "funcao": u.funcao or u.posicao,
        "squad": u.squad,
        "posicao": u.posicao,
        "nivel_acesso": u.nivel_acesso,
        "ativo": u.ativo,
        "senioridade": u.senioridade,
        "nivel": u.nivel
    } for u in users], safe=False)

@login_required
@csrf_exempt
def api_save_usuario(request):
    if request.user.nivel_acesso != "Admin":
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        email = data.get("email")
        
        if not email:
            return JsonResponse({"error": "Email é obrigatório"}, status=400)
            
        user, created = Investidor.objects.update_or_create(
            email=email,
            defaults={
                "nome": data.get("nome"),
                "funcao": data.get("funcao"),
                "senioridade": data.get("senioridade"),
                "nivel": data.get("nivel"),
                "squad": data.get("squad"),
                "posicao": data.get("posicao"),
                "nivel_acesso": data.get("nivel_acesso"),
                "ativo": str(data.get("ativo")).lower() == "true",
            }
        )
        
        # Se for novo, gera senha padrão ou a fornecida
        if created or data.get("password"):
            password = data.get("password") or "v4company"
            user.set_password(password)
            user.save()
            
        return JsonResponse({"status": "success"})

@login_required
@csrf_exempt
def api_reset_password(request):
    if request.user.nivel_acesso != "Admin":
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        email = data.get("email")
        password = data.get("password")
        
        try:
            user = Investidor.objects.get(email=email)
            user.set_password(password)
            user.save()
            return JsonResponse({"status": "success"})
        except Investidor.DoesNotExist:
            return JsonResponse({"error": "Usuário não encontrado"}, status=404)
