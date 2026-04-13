from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class InvestidorManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O e-mail é obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('nivel_acesso', 'Admin')
        return self.create_user(email, password, **extra_fields)

class Investidor(AbstractBaseUser, PermissionsMixin):
    last_login = None
    is_superuser = None
    groups = None
    user_permissions = None
    is_staff = None
    is_active = None
    nome = models.CharField(max_length=100)
    email = models.EmailField(max_length=50, unique=True)
    funcao = models.CharField(max_length=50, null=True, blank=True)
    senioridade = models.CharField(max_length=50, null=True, blank=True)
    squad = models.CharField(max_length=100, null=True, blank=True)
    password = models.CharField(max_length=250, db_column='senha') # Mapeado para o campo 'senha' do Flask
    nivel_acesso = models.CharField(max_length=10, default='Usuário')
    ativo = models.BooleanField(default=True)
    cpf = models.CharField(max_length=11, null=True, blank=True)
    telefone = models.CharField(max_length=15, null=True, blank=True)
    nivel = models.TextField(null=True, blank=True)
    profile_picture = models.CharField(max_length=250, null=True, blank=True)
    posicao = models.CharField(max_length=250, null=True, blank=True)
    
    # Django fields (Disabled for legacy DB compatibility)

    objects = InvestidorManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    class Meta:
        db_table = '"plataforma_geral"."investidores"'
        managed = False # Importante: não queremos que o Django tente alterar esta tabela

    def __str__(self):
        return self.nome

class Auth(models.Model):
    id = models.IntegerField(primary_key=True)
    email = models.CharField(max_length=50)
    token = models.CharField(max_length=30)

    class Meta:
        db_table = '"plataforma_geral"."auth"'
        managed = False
