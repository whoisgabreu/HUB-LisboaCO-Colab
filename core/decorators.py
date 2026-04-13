from functools import wraps
from django.shortcuts import render
from django.core.exceptions import PermissionDenied

def check_access(roles):
    """Decorator para verificar cargo do usuário."""
    def decorator(f):
        @wraps(f)
        def wrapper(request, *args, **kwargs):
            user_role = (request.user.funcao or "").strip()
            user_posicao = (request.user.posicao or "").strip()
            
            # Se for Gerência ou Sócio via posição, concede acesso a quase tudo
            is_high_level = user_posicao in ["Gerência", "Sócio"]
            
            # Verifica se o cargo solicitado está na lista ou se é Gerência/Sócio
            if not is_high_level and not any(role.lower() == user_role.lower() for role in roles):
                return render(request, "index.html", {"error": "Acesso restrito."})
            return f(request, *args, **kwargs)
        return wrapper
    return decorator
