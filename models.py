from sqlalchemy import Column, Integer, String, Boolean, Date, Text, DECIMAL, BigInteger, FetchedValue
from sqlalchemy.dialects.postgresql import JSONB
from database import Base


class Investidor(Base):
    """Tabela: plataforma_geral.investidores"""
    __tablename__ = "investidores"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer, primary_key=True)
    nome = Column(String(100))
    email = Column(String(50))
    funcao = Column(String(50))
    senioridade = Column(String(50))
    squad = Column(String(100))
    senha = Column(String(250))
    nivel_acesso = Column(String(10))
    ativo = Column(Boolean)
    cpf = Column(String(11))
    telefone = Column(String(15))
    nivel = Column(Text)


class Auth(Base):
    """Tabela: plataforma_geral.auth"""
    __tablename__ = "auth"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer)
    email = Column(String(50), primary_key=True)
    token = Column(String(30))


class ProjetoAtivo(Base):
    """Tabela: plataforma_geral.projetos_ativos"""
    __tablename__ = "projetos_ativos"
    __table_args__ = {"schema": "plataforma_geral"}

    pipefy_id = Column(Integer, primary_key=True)
    id = Column(Integer)
    nome = Column(String(250))
    documento = Column(String(250))
    fee = Column(Integer)
    moeda = Column(String(6))
    squad_atribuida = Column(String(20))
    produto_contratado = Column(String(250))
    data_de_inicio = Column(Date)
    cohort = Column(String(100))
    meta_account_id = Column(String(100))
    google_account_id = Column(String(100))
    fase_do_pipefy = Column(String(100))
    url_webhook_gchat = Column(String(250))
    step = Column(String(15))
    informacoes_gerais = Column(String(1500))
    orcamento_midia_meta = Column(Integer)
    orcamento_midia_google = Column(Integer)
    data_fim = Column(Date)
    extra = Column(JSONB)
    notas = Column(JSONB)
    ekyte_workspace = Column(String(2500))


class ProjetoOnetime(Base):
    """Tabela: plataforma_geral.projetos_onetime"""
    __tablename__ = "projetos_onetime"
    __table_args__ = {"schema": "plataforma_geral"}

    pipefy_id = Column(Integer, primary_key=True)
    id = Column(Integer)
    nome = Column(String(250))
    documento = Column(String(250))
    fee = Column(Integer)
    moeda = Column(String(6))
    squad_atribuida = Column(String(20))
    produto_contratado = Column(String(250))
    data_de_inicio = Column(Date)
    cohort = Column(String(100))
    meta_account_id = Column(String(100))
    google_account_id = Column(String(100))
    fase_do_pipefy = Column(String(100))
    url_webhook_gchat = Column(String(250))
    step = Column(String(15))
    informacoes_gerais = Column(String(1500))
    orcamento_midia_meta = Column(Integer)
    orcamento_midia_google = Column(Integer)
    data_fim = Column(Date)
    extra = Column(JSONB)
    notas = Column(JSONB)
    ekyte_workspace = Column(String(2500))


class ProjetoInativo(Base):
    """Tabela: plataforma_geral.projetos_inativos"""
    __tablename__ = "projetos_inativos"
    __table_args__ = {"schema": "plataforma_geral"}

    pipefy_id = Column(Integer, primary_key=True)
    id = Column(Integer)
    nome = Column(String(250))
    documento = Column(String(250))
    fee = Column(Integer)
    moeda = Column(String(6))
    squad_atribuida = Column(String(20))
    produto_contratado = Column(String(250))
    data_de_inicio = Column(Date)
    cohort = Column(String(100))
    meta_account_id = Column(String(100))
    google_account_id = Column(String(100))
    fase_do_pipefy = Column(String(100))
    url_webhook_gchat = Column(String(250))
    step = Column(String(15))
    informacoes_gerais = Column(String(1500))
    orcamento_midia_meta = Column(Integer)
    orcamento_midia_google = Column(Integer)
    data_fim = Column(Date)
    extra = Column(JSONB)
    notas = Column(JSONB)
    ekyte_workspace = Column(String(2500))


class RemuneracaoCargo(Base):
    """Tabela: plataforma_geral.remuneracao_cargos"""
    __tablename__ = "remuneracao_cargos"
    __table_args__ = {"schema": "plataforma_geral"}

    fixo_cargo = Column(String(50), primary_key=True)
    fixo_senioridade = Column(String(50), primary_key=True)
    fixo_level = Column(String(50), primary_key=True)
    fixo_ticket_medio = Column(DECIMAL(15, 2))
    fixo_mrr_esperado = Column(DECIMAL(15, 2))
    fixo_mrr_teto = Column(DECIMAL(15, 2))
    fixo_remuneracao_fixa = Column(DECIMAL(15, 2))
    fixo_churn_maximo_percentual = Column(DECIMAL(8, 7))

    # Campos calculados
    calc_mrr_minima = Column(DECIMAL(15, 2))
    calc_remuneracao_minima = Column(DECIMAL(15, 2))
    calc_remuneracao_maxima = Column(DECIMAL(15, 2))
    calc_csp_esperado = Column(DECIMAL(8, 7))
    calc_churn_maximo_valor = Column(DECIMAL(15, 2))


class InvestidorProjeto(Base):
    """Tabela: plataforma_geral.investidores_projetos"""
    __tablename__ = "investidores_projetos"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer, primary_key=True)
    email_investidor = Column(String(250), primary_key=True)
    pipefy_id_projeto = Column(Integer)
    active = Column(Boolean)
    inactivated_at = Column(Date)
    created_at = Column(Date)
    cientista = Column(Boolean)
    nome_projeto = Column(String(250))
    fee_projeto = Column(DECIMAL(15, 2))
    fee_contribuicao = Column(DECIMAL(15, 2))


class MetricaMensal(Base):
    """Tabela: plataforma_geral.investidores_metricas_mensais_novo"""
    __tablename__ = "investidores_metricas_mensais_novo"
    __table_args__ = {"schema": "plataforma_geral"}

    # Chave composta: email + mes + ano
    email_investidor = Column(Text, primary_key=True)
    mes = Column(Integer, primary_key=True)
    ano = Column(Integer, primary_key=True)

    detalhes = Column(JSONB)
    cargo = Column(Text)
    senioridade = Column(Text)
    level = Column(Text)
    flag = Column(Text)
    motivo_flag = Column(Text)
    green_streak = Column(Integer)
    yellow_streak = Column(Integer)

    fixo_mrr_atual = Column(DECIMAL(15, 2))
    fixo_mrr_entrega = Column(DECIMAL(15, 2))  # Nova coluna para MRR de entregas
    fixo_churn_atual = Column(DECIMAL(15, 2))
    fixo_remuneracao_fixa = Column(DECIMAL(15, 2))
    fixo_csp_esperado = Column(DECIMAL(8, 7))
    fixo_churn_maximo_percentual = Column(DECIMAL(8, 7))
    fixo_mrr_minimo = Column(DECIMAL(15, 2))
    fixo_mrr_esperado = Column(DECIMAL(15, 2))
    fixo_mrr_teto = Column(DECIMAL(15, 2))
    fixo_churn_maximo_valor = Column(DECIMAL(15, 2))
    fixo_remuneracao_minima = Column(DECIMAL(15, 2))
    fixo_remuneracao_maxima = Column(DECIMAL(15, 2))
    fixo_mrr_projeto_total = Column(DECIMAL(15, 2))  # Novo campo comparativo

    # Campos calculados pelo banco (GENERATED ALWAYS AS STORED)
    calc_churn_real_percentual = Column(DECIMAL(8, 7), server_default=FetchedValue())
    calc_delta_churn_percentual = Column(DECIMAL(8, 7), server_default=FetchedValue())
    calc_delta_churn_valor = Column(DECIMAL(15, 2), server_default=FetchedValue())
    calc_variavel_churn = Column(DECIMAL(15, 2), server_default=FetchedValue())
    calc_delta_csp = Column(DECIMAL(8, 7), server_default=FetchedValue())
    calc_variavel_csp = Column(DECIMAL(15, 2), server_default=FetchedValue())
    calc_variavel_total = Column(DECIMAL(15, 2), server_default=FetchedValue())
    calc_remuneracao_total = Column(DECIMAL(15, 2), server_default=FetchedValue())

    def to_dict(self):
        """Converte para dict compatível com o formato que o template espera."""
        return {
            "email": self.email_investidor,
            "squad": None,  # será preenchido com JOIN do investidor se necessário
            "role": self.cargo,
            "id": f"inv_{self.email_investidor.replace('@', '_').replace('.', '_')}",
            "name": None,  # será preenchido com JOIN do investidor
            "fixed_fee": float(self.fixo_remuneracao_fixa or 0),
            "mrr": float(self.fixo_mrr_atual or 0),
            "churn": float(self.fixo_churn_atual or 0),
            "flag": self.flag,
            "green_streak": self.green_streak or 0,
            "yellow_streak": self.yellow_streak or 0,
            "rows": [],  # histórico mensal — será agregado depois
        }


class OperacaoTarefa(Base):
    """Tabela: plataforma_geral.operacao_tarefas"""
    __tablename__ = "operacao_tarefas"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer, primary_key=True)
    projeto_pipefy_id = Column(Integer, nullable=False)
    tipo = Column(String(20), nullable=False) # 'semanal' ou 'quarter'
    descricao = Column(Text, nullable=False)
    concluida = Column(Boolean, default=False)
    referencia = Column(String(20), nullable=False) # '2026-W08' ou '2026-Q1'
    ano = Column(Integer, nullable=False)
    created_at = Column(Date)


class OperacaoEntregaMensal(Base):
    """Tabela: plataforma_geral.operacao_entregas_mensais"""
    __tablename__ = "operacao_entregas_mensais"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer, primary_key=True)
    investidor_email = Column(Text, nullable=False)
    projeto_pipefy_id = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    ano = Column(Integer, nullable=False)
    entrega_1 = Column(Boolean, default=False)
    entrega_2 = Column(Boolean, default=False)
    entrega_3 = Column(Boolean, default=False)
    entrega_4 = Column(Boolean, default=False)
    percentual_calculado = Column(DECIMAL(3, 2), default=0)
    valor_fee_original = Column(DECIMAL(15, 2), default=0)
    valor_contribuicao_mrr = Column(DECIMAL(15, 2), default=0)
    created_at = Column(Date)
    updated_at = Column(Date)
