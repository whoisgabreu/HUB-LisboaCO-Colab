"""Modelos isolados do Feed social do HUB.

Novas tabelas em ``plataforma_geral``. Não alteram os models existentes.
"""

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


class FeedPost(Base):
    """Tabela: plataforma_geral.feed_posts"""

    __tablename__ = "feed_posts"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer, primary_key=True)
    autor_email = Column(String(255))
    tipo = Column(String(20), nullable=False, default="post")  # post | evento | aniversario
    titulo = Column(String(200))
    conteudo = Column(Text)
    evento_data = Column(DateTime)
    evento_local = Column(String(200))
    fixado = Column(Boolean, nullable=False, default=False)
    fixado_ate = Column(DateTime)
    deletado = Column(Boolean, nullable=False, default=False)
    criado_em = Column(DateTime, server_default=FetchedValue())
    atualizado_em = Column(DateTime)


class FeedReacao(Base):
    """Tabela: plataforma_geral.feed_reacoes"""

    __tablename__ = "feed_reacoes"
    __table_args__ = (
        UniqueConstraint("post_id", "usuario_email", name="uq_feed_reacao_usuario"),
        {"schema": "plataforma_geral"},
    )

    id = Column(Integer, primary_key=True)
    post_id = Column(
        Integer,
        ForeignKey("plataforma_geral.feed_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    usuario_email = Column(String(255), nullable=False)
    tipo = Column(String(20), nullable=False)  # like | love | haha | wow | sad | angry
    criado_em = Column(DateTime, server_default=FetchedValue())


class FeedComentario(Base):
    """Tabela: plataforma_geral.feed_comentarios"""

    __tablename__ = "feed_comentarios"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer, primary_key=True)
    post_id = Column(
        Integer,
        ForeignKey("plataforma_geral.feed_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id = Column(
        Integer,
        ForeignKey("plataforma_geral.feed_comentarios.id", ondelete="CASCADE"),
    )
    autor_email = Column(String(255), nullable=False)
    conteudo = Column(Text, nullable=False)
    deletado = Column(Boolean, nullable=False, default=False)
    criado_em = Column(DateTime, server_default=FetchedValue())
