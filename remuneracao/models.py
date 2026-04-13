from django.db import models

class RemuneracaoCargo(models.Model):
    fixo_cargo = models.CharField(max_length=50, primary_key=True)
    fixo_senioridade = models.CharField(max_length=50) # PK composta no SQL, Django usará fixo_cargo como PK base se não especificada
    fixo_level = models.CharField(max_length=50)
    fixo_ticket_medio = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixo_mrr_esperado = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixo_mrr_teto = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixo_remuneracao_fixa = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixo_churn_maximo_percentual = models.DecimalField(max_digits=8, decimal_places=7, null=True, blank=True)

    # Campos calculados (podem ser preenchidos no Python ou via SQL)
    calc_media_clientes = models.IntegerField(null=True, blank=True)
    calc_csp_esperado = models.DecimalField(max_digits=8, decimal_places=7, null=True, blank=True)
    calc_mrr_minima = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    calc_variavel_csp_teto_percentual = models.DecimalField(max_digits=8, decimal_places=7, null=True, blank=True)
    calc_variavel_csp_teto_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    calc_remuneracao_minima = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    calc_remuneracao_maxima = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    calc_range_total_remuneracao = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    calc_percentual_range_remuneracao = models.DecimalField(max_digits=8, decimal_places=7, null=True, blank=True)
    calc_churn_maximo_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = '"plataforma_geral"."remuneracao_cargos"'
        managed = False
        unique_together = (('fixo_cargo', 'fixo_senioridade', 'fixo_level'),)

class MetricaMensal(models.Model):
    ativo = models.BooleanField(null=True, blank=True)

    # Chave composta: email + mes + ano. Django usará email_investidor como PK principal para o ORM.
    email_investidor = models.TextField(primary_key=True)
    mes = models.IntegerField()
    ano = models.IntegerField()

    detalhes = models.JSONField(null=True, blank=True)
    cargo = models.TextField(null=True, blank=True)
    senioridade = models.TextField(null=True, blank=True)
    level = models.TextField(null=True, blank=True)
    flag = models.TextField(null=True, blank=True)
    motivo_flag = models.TextField(null=True, blank=True)
    green_streak = models.IntegerField(null=True, blank=True)
    yellow_streak = models.IntegerField(null=True, blank=True)

    fixo_mrr_atual = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixo_mrr_entrega = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixo_churn_atual = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixo_remuneracao_fixa = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixo_csp_esperado = models.DecimalField(max_digits=8, decimal_places=7, null=True, blank=True)
    fixo_churn_maximo_percentual = models.DecimalField(max_digits=8, decimal_places=7, null=True, blank=True)
    fixo_mrr_minimo = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixo_mrr_esperado = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixo_mrr_teto = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixo_churn_maximo_valor = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixo_remuneracao_minima = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixo_remuneracao_maxima = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixo_mrr_projeto_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Campos calculados pelo banco (GENERATED ALWAYS AS STORED) - Marcados como editable=False
    calc_churn_real_percentual = models.DecimalField(max_digits=8, decimal_places=7, editable=False, null=True, blank=True)
    calc_delta_churn_percentual = models.DecimalField(max_digits=8, decimal_places=7, editable=False, null=True, blank=True)
    calc_delta_churn_valor = models.DecimalField(max_digits=15, decimal_places=2, editable=False, null=True, blank=True)
    calc_variavel_churn = models.DecimalField(max_digits=15, decimal_places=2, editable=False, null=True, blank=True)
    calc_delta_csp = models.DecimalField(max_digits=8, decimal_places=7, editable=False, null=True, blank=True)
    calc_variavel_csp = models.DecimalField(max_digits=15, decimal_places=2, editable=False, null=True, blank=True)
    calc_variavel_total = models.DecimalField(max_digits=15, decimal_places=2, editable=False, null=True, blank=True)
    calc_remuneracao_total = models.DecimalField(max_digits=15, decimal_places=2, editable=False, null=True, blank=True)
    historico_projetos = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = '"plataforma_geral"."investidores_metricas_mensais_novo"'
        managed = False
        unique_together = (('email_investidor', 'mes', 'ano'),)
