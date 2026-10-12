"""Modelos isolados do Chat interno do HUB (1:1)."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    FetchedValue,
)

from database import Base


class ChatConversa(Base):
    """Tabela: plataforma_geral.chat_conversas"""

    __tablename__ = "chat_conversas"
    __table_args__ = (
        UniqueConstraint("user_a", "user_b", name="uq_chat_conversa_par"),
        {"schema": "plataforma_geral"},
    )

    id = Column(Integer, primary_key=True)
    user_a = Column(String(255), nullable=False)
    user_b = Column(String(255), nullable=False)
    criado_em = Column(DateTime, server_default=FetchedValue())
    ultima_mensagem_em = Column(DateTime)


class ChatMensagem(Base):
    """Tabela: plataforma_geral.chat_mensagens"""

    __tablename__ = "chat_mensagens"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(BigInteger, primary_key=True)
    conversa_id = Column(
        Integer,
        ForeignKey("plataforma_geral.chat_conversas.id", ondelete="CASCADE"),
        nullable=False,
    )
    autor_email = Column(String(255), nullable=False)
    conteudo = Column(Text, nullable=False)
    deletado = Column(Boolean, nullable=False, default=False)
    editado = Column(Boolean, nullable=False, default=False)
    editado_em = Column(DateTime)
    criado_em = Column(DateTime, server_default=FetchedValue())


class ChatLeitura(Base):
    """Tabela: plataforma_geral.chat_leituras"""

    __tablename__ = "chat_leituras"
    __table_args__ = (
        UniqueConstraint("conversa_id", "usuario_email", name="uq_chat_leitura"),
        {"schema": "plataforma_geral"},
    )

    id = Column(Integer, primary_key=True)
    conversa_id = Column(
        Integer,
        ForeignKey("plataforma_geral.chat_conversas.id", ondelete="CASCADE"),
        nullable=False,
    )
    usuario_email = Column(String(255), nullable=False)
    ultima_lida_msg_id = Column(BigInteger, nullable=False, default=0)
    ultima_lida_em = Column(DateTime)


class ChatPresenca(Base):
    """Tabela: plataforma_geral.chat_presenca"""

    __tablename__ = "chat_presenca"
    __table_args__ = {"schema": "plataforma_geral"}

    usuario_email = Column(String(255), primary_key=True)
    ultimo_ping = Column(DateTime)
