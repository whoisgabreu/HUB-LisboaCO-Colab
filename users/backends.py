from django.contrib.auth.backends import ModelBackend
from werkzeug.security import check_password_hash
from .models import Investidor

class InvestidorBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get('email')
        try:
            user = Investidor.objects.get(email=email)
            if check_password_hash(user.password, password):
                return user
        except Investidor.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        try:
            return Investidor.objects.get(pk=user_id)
        except Investidor.DoesNotExist:
            return None
