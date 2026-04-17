from sqlalchemy import Column, Integer, String, Boolean, Date, Text, DECIMAL, BigInteger, FetchedValue, DateTime, UniqueConstraint
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
    profile_picture = Column(String(250))
    posicao = Column(String(250))


class Auth(Base):
    """Tabela: plataforma_geral.auth"""
    __tablename__ = "auth"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer, autoincrement=True)
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

    ativo = Column(Boolean)

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
    historico_projetos = Column(JSONB)
    entregas_criativos = Column(JSONB)  # Array de entregas criativas por projeto


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


class OperacaoPlanoMidia(Base):
    """Tabela: plataforma_geral.operacao_planos_midia"""
    __tablename__ = "operacao_planos_midia"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer, primary_key=True)
    projeto_pipefy_id = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    ano = Column(Integer, nullable=False)
    investidor_email = Column(Text, nullable=False)
    dados_plano = Column(JSONB, nullable=False) # Lista de canais, campanhas, orçamentos
    created_at = Column(Date)
    updated_at = Column(Date)


class OperacaoOtimizacao(Base):
    """Tabela: plataforma_geral.operacao_otimizacoes"""
    __tablename__ = "operacao_otimizacoes"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer, primary_key=True)
    projeto_pipefy_id = Column(Integer, nullable=False)
    investidor_email = Column(Text, nullable=False)
    tipo = Column(String(50)) # Campanha, Criativo, GTM, etc.
    canal = Column(String(50)) # Meta, Google, etc.
    data_otimizacao = Column(Date, nullable=False)
    detalhes = Column(Text)
    created_at = Column(Date)


class OperacaoCheckin(Base):
    """Tabela: plataforma_geral.operacao_checkins"""
    __tablename__ = "operacao_checkins"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer, primary_key=True)
    projeto_pipefy_id = Column(Integer, nullable=False)
    investidor_email = Column(Text, nullable=False)
    semana_ano = Column(String(20), nullable=False) # Ex: 2026-W09
    
    # Novas Perguntas (V8.0)
    compareceu = Column(Boolean, default=False)
    campanhas_ativas = Column(Boolean, default=True)
    gap_comunicacao = Column(Boolean, default=False)
    cliente_reclamou = Column(Boolean, default=False)
    
    # Legado / Métricas
    satisfeito = Column(Boolean, default=True)
    csat_pontuacao = Column(Integer)
    observacoes = Column(Text)
    created_at = Column(Date)


class MonthlyDelivery(Base):
    """
    Tabela: plataforma_geral.monthly_deliveries
    Entregas mensais fixas, geradas automaticamente por cargo.
    Isoladas por: usuário + cliente + cargo + tipo + competência.
    UNIQUE constraint garante idempotência (sem duplicatas).
    """
    __tablename__ = "monthly_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "email", "client_id", "role", "delivery_type", "month", "year",
            name="uq_monthly_delivery_per_user_client_role"
        ),
        {"schema": "plataforma_geral"}
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)                           # FK → investidores.id
    client_id = Column(Integer, nullable=False)         # FK → projetos_ativos.pipefy_id
    email = Column(Text, nullable=False)
    role = Column(String(50), nullable=False)           # 'Account' | 'Gestor de Tráfego'
    delivery_type = Column(String(100), nullable=False)  # 'checkin', 'plano_midia', etc.
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    status = Column(String(20), default='pending')      # 'pending' | 'completed'
    completed_at = Column(DateTime)
    fee_snapshot = Column(DECIMAL(15, 2))               # fee no momento do cálculo
    mrr_contribution = Column(DECIMAL(15, 2))           # fee_snapshot * 0.25
    created_at = Column(DateTime)


class EntregaCriativa(Base):
    """
    Tabela: plataforma_geral.investidores_entregas_mensais_novos
    Armazena as entregas criativas (criativos, vídeos, LPs, copys) por designer, mês e ano.
    O campo entregas_criativos é um array JSONB com uma entrada por projeto:
    [{"cliente": str, "projeto_id": str, "criativos": {...}, "videos": {...}, "lp": {...}}]
    """
    __tablename__ = "investidores_entregas_mensais_novos"
    __table_args__ = {"schema": "plataforma_geral"}

    email_investidor = Column(Text, primary_key=True)
    mes = Column(Integer, primary_key=True)
    ano = Column(Integer, primary_key=True)
    entregas_criativos = Column(JSONB, default=list)
    updated_at = Column(DateTime)


class OperacaoLinkUtil(Base):
    """Tabela: plataforma_geral.operacao_links_uteis"""
    __tablename__ = "operacao_links_uteis"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer, primary_key=True)
    projeto_pipefy_id = Column(Integer, nullable=False)
    titulo = Column(String(200), nullable=False)
    url = Column(Text, nullable=False)
    descricao = Column(Text)
    icone = Column(String(50), default='fa-link')
    criado_por = Column(Text)
    created_at = Column(DateTime)
