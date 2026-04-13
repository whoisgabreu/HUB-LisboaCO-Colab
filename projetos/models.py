from django.db import models

class ProjetoBase(models.Model):
    pipefy_id = models.IntegerField(primary_key=True)
    id = models.IntegerField(null=True, blank=True)
    nome = models.CharField(max_length=250, null=True, blank=True)
    documento = models.CharField(max_length=250, null=True, blank=True)
    fee = models.IntegerField(null=True, blank=True)
    moeda = models.CharField(max_length=6, null=True, blank=True)
    squad_atribuida = models.CharField(max_length=20, null=True, blank=True)
    produto_contratado = models.CharField(max_length=250, null=True, blank=True)
    data_de_inicio = models.DateField(null=True, blank=True)
    cohort = models.CharField(max_length=100, null=True, blank=True)
    meta_account_id = models.CharField(max_length=100, null=True, blank=True)
    google_account_id = models.CharField(max_length=100, null=True, blank=True)
    fase_do_pipefy = models.CharField(max_length=100, null=True, blank=True)
    url_webhook_gchat = models.CharField(max_length=250, null=True, blank=True)
    step = models.CharField(max_length=15, null=True, blank=True)
    informacoes_gerais = models.CharField(max_length=1500, null=True, blank=True)
    orcamento_midia_meta = models.IntegerField(null=True, blank=True)
    orcamento_midia_google = models.IntegerField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    extra = models.JSONField(null=True, blank=True)
    notas = models.JSONField(null=True, blank=True)
    ekyte_workspace = models.CharField(max_length=2500, null=True, blank=True)

    class Meta:
        abstract = True
        managed = False

class ProjetoAtivo(ProjetoBase):
    class Meta(ProjetoBase.Meta):
        db_table = '"plataforma_geral"."projetos_ativos"'

class ProjetoOnetime(ProjetoBase):
    class Meta(ProjetoBase.Meta):
        db_table = '"plataforma_geral"."projetos_onetime"'

class ProjetoInativo(ProjetoBase):
    class Meta(ProjetoBase.Meta):
        db_table = '"plataforma_geral"."projetos_inativos"'

class InvestidorProjeto(models.Model):
    # Django não gosta de chaves compostas. Vamos usar o 'id' como PK se possível.
    # Mas no SQLAlchemy estava definido id e email_investidor como primárias.
    # Se o banco tem uma coluna 'id' autoincrement ou única, usamos ela.
    id = models.IntegerField(primary_key=True)
    email_investidor = models.CharField(max_length=250)
    pipefy_id_projeto = models.IntegerField()
    active = models.BooleanField()
    inactivated_at = models.DateField(null=True, blank=True)
    created_at = models.DateField(null=True, blank=True)
    cientista = models.BooleanField()
    nome_projeto = models.CharField(max_length=250, null=True, blank=True)
    fee_projeto = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fee_contribuicao = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = '"plataforma_geral"."investidores_projetos"'
        managed = False
