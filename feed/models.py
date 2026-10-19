"""Modelos isolados do Feed social do HUB.

Novas tabelas em ``plataforma_geral``. Não alteram os models existentes.
"""

from sqlalchemy import (
    ARRAY,
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
from sqlalchemy.dialects.postgresql import JSONB

from database import Base


class FeedPost(Base):
    """Tabela: plataforma_geral.feed_posts"""

    __tablename__ = "feed_posts"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer, primary_key=True)
    autor_email = Column(String(255))
    # post | evento | aniversario | enquete | repost
    tipo = Column(String(20), nullable=False, default="post")
    titulo = Column(String(200))
    conteudo = Column(Text)
    evento_data = Column(DateTime)
    evento_local = Column(String(200))
    fixado = Column(Boolean, nullable=False, default=False)
    fixado_ate = Column(DateTime)
    deletado = Column(Boolean, nullable=False, default=False)
    # todos | squad | gestao
    visibilidade = Column(String(20), nullable=False, default="todos")
    # Canais de envio (v2): público + squads de destino
    dest_todos = Column(Boolean, nullable=False, default=False)
    squads_destino = Column(ARRAY(Integer), nullable=False, default=list)
    original_post_id = Column(Integer)
    enquete = Column(JSONB)
    # Lista de imagens anexadas: [{arquivo, largura, altura}]
    imagens = Column(JSONB, nullable=False, default=list)
    editado = Column(Boolean, nullable=False, default=False)
    total_edicoes = Column(Integer, nullable=False, default=0)
    editado_em = Column(DateTime)
    oculto = Column(Boolean, nullable=False, default=False)
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


class FeedComentarioReacao(Base):
    """Tabela: plataforma_geral.feed_comentario_reacoes"""

    __tablename__ = "feed_comentario_reacoes"
    __table_args__ = (
        UniqueConstraint("comentario_id", "usuario_email", name="uq_feed_coment_reacao"),
        {"schema": "plataforma_geral"},
    )

    id = Column(Integer, primary_key=True)
    comentario_id = Column(
        Integer,
        ForeignKey("plataforma_geral.feed_comentarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    usuario_email = Column(String(255), nullable=False)
    tipo = Column(String(20), nullable=False)
    criado_em = Column(DateTime, server_default=FetchedValue())


class FeedSalvo(Base):
    """Tabela: plataforma_geral.feed_salvos"""

    __tablename__ = "feed_salvos"
    __table_args__ = (
        UniqueConstraint("usuario_email", "post_id", name="uq_feed_salvo"),
        {"schema": "plataforma_geral"},
    )

    id = Column(Integer, primary_key=True)
    usuario_email = Column(String(255), nullable=False)
    post_id = Column(
        Integer,
        ForeignKey("plataforma_geral.feed_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    criado_em = Column(DateTime, server_default=FetchedValue())


class FeedEnqueteVoto(Base):
    """Tabela: plataforma_geral.feed_enquete_votos"""

    __tablename__ = "feed_enquete_votos"
    __table_args__ = (
        UniqueConstraint("post_id", "usuario_email", name="uq_feed_enquete_voto"),
        {"schema": "plataforma_geral"},
    )

    id = Column(Integer, primary_key=True)
    post_id = Column(
        Integer,
        ForeignKey("plataforma_geral.feed_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    usuario_email = Column(String(255), nullable=False)
    opcao_index = Column(Integer, nullable=False)
    criado_em = Column(DateTime, server_default=FetchedValue())


class FeedDenuncia(Base):
    """Tabela: plataforma_geral.feed_denuncias"""

    __tablename__ = "feed_denuncias"
    __table_args__ = (
        UniqueConstraint("post_id", "usuario_email", name="uq_feed_denuncia"),
        {"schema": "plataforma_geral"},
    )

    id = Column(Integer, primary_key=True)
    post_id = Column(
        Integer,
        ForeignKey("plataforma_geral.feed_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    usuario_email = Column(String(255), nullable=False)
    motivo = Column(Text)
    criado_em = Column(DateTime, server_default=FetchedValue())


class FeedPostEdicao(Base):
    """Tabela: plataforma_geral.feed_posts_edicoes (auditoria)"""

    __tablename__ = "feed_posts_edicoes"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer, primary_key=True)
    post_id = Column(
        Integer,
        ForeignKey("plataforma_geral.feed_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    conteudo_anterior = Column(Text)
    editado_em = Column(DateTime, server_default=FetchedValue())
    editado_por = Column(String(255))


class FeedNotificacao(Base):
    """Tabela: plataforma_geral.feed_notificacoes"""

    __tablename__ = "feed_notificacoes"
    __table_args__ = {"schema": "plataforma_geral"}

    id = Column(Integer, primary_key=True)
    usuario_email = Column(String(255), nullable=False)
    tipo = Column(String(30), nullable=False)  # reacao | comentario | resposta | mencao
    ator_email = Column(String(255))
    post_id = Column(Integer)
    comentario_id = Column(Integer)
    texto = Column(String(400))
    lida = Column(Boolean, nullable=False, default=False)
    criado_em = Column(DateTime, server_default=FetchedValue())
