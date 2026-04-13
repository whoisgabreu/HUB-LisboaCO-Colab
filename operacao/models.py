from django.db import models

class OperacaoTarefa(models.Model):
    projeto_pipefy_id = models.IntegerField()
    tipo = models.CharField(max_length=20)
    descricao = models.TextField()
    concluida = models.BooleanField(default=False)
    referencia = models.CharField(max_length=20)
    ano = models.IntegerField()
    created_at = models.DateField(null=True, blank=True)

    class Meta:
        db_table = '"plataforma_geral"."operacao_tarefas"'
        managed = False

class OperacaoEntregaMensal(models.Model):
    investidor_email = models.TextField()
    projeto_pipefy_id = models.IntegerField()
    mes = models.IntegerField()
    ano = models.IntegerField()
    entrega_1 = models.BooleanField(default=False)
    entrega_2 = models.BooleanField(default=False)
    entrega_3 = models.BooleanField(default=False)
    entrega_4 = models.BooleanField(default=False)
    percentual_calculado = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    valor_fee_original = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    valor_contribuicao_mrr = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateField(null=True, blank=True)
    updated_at = models.DateField(null=True, blank=True)

    class Meta:
        db_table = '"plataforma_geral"."operacao_entregas_mensais"'
        managed = False

class OperacaoPlanoMidia(models.Model):
    projeto_pipefy_id = models.IntegerField()
    mes = models.IntegerField()
    ano = models.IntegerField()
    investidor_email = models.TextField()
    dados_plano = models.JSONField()
    created_at = models.DateField(null=True, blank=True)
    updated_at = models.DateField(null=True, blank=True)

    class Meta:
        db_table = '"plataforma_geral"."operacao_planos_midia"'
        managed = False

class OperacaoOtimizacao(models.Model):
    projeto_pipefy_id = models.IntegerField()
    investidor_email = models.TextField()
    tipo = models.CharField(max_length=50, null=True, blank=True)
    canal = models.CharField(max_length=50, null=True, blank=True)
    data_otimizacao = models.DateField()
    detalhes = models.TextField(null=True, blank=True)
    created_at = models.DateField(null=True, blank=True)

    class Meta:
        db_table = '"plataforma_geral"."operacao_otimizacoes"'
        managed = False

class OperacaoCheckin(models.Model):
    projeto_pipefy_id = models.IntegerField()
    investidor_email = models.TextField()
    semana_ano = models.CharField(max_length=20)
    compareceu = models.BooleanField(default=False)
    campanhas_ativas = models.BooleanField(default=True)
    gap_comunicacao = models.BooleanField(default=False)
    cliente_reclamou = models.BooleanField(default=False)
    satisfeito = models.BooleanField(default=True)
    csat_pontuacao = models.IntegerField(null=True, blank=True)
    observacoes = models.TextField(null=True, blank=True)
    created_at = models.DateField(null=True, blank=True)

    class Meta:
        db_table = '"plataforma_geral"."operacao_checkins"'
        managed = False

class MonthlyDelivery(models.Model):
    user_id = models.IntegerField(null=True, blank=True)
    client_id = models.IntegerField()
    email = models.TextField()
    role = models.CharField(max_length=50)
    delivery_type = models.CharField(max_length=100)
    month = models.IntegerField()
    year = models.IntegerField()
    status = models.CharField(max_length=20, default='pending')
    completed_at = models.DateTimeField(null=True, blank=True)
    fee_snapshot = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    mrr_contribution = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = '"plataforma_geral"."monthly_deliveries"'
        managed = False
        constraints = [
            models.UniqueConstraint(
                fields=['email', 'client_id', 'role', 'delivery_type', 'month', 'year'],
                name='uq_monthly_delivery_per_user_client_role'
            )
        ]

class OperacaoLinkUtil(models.Model):
    projeto_pipefy_id = models.IntegerField()
    titulo = models.CharField(max_length=200)
    url = models.TextField()
    descricao = models.TextField(null=True, blank=True)
    icone = models.CharField(max_length=50, default='fa-link')
    criado_por = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = '"plataforma_geral"."operacao_links_uteis"'
        managed = False
