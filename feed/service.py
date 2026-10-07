"""Serviço isolado do Feed social do HUB.

Responsável pelas regras de posts, reações, comentários e pelo post
automático de aniversário. Não altera services existentes.
"""

from datetime import datetime, date, time, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from models import Investidor
from feed.models import FeedComentario, FeedPost, FeedReacao

TZ = ZoneInfo("America/Sao_Paulo")

REACOES_VALIDAS = ["like", "love", "haha", "wow", "sad", "angry"]

# Cache em memória: evita reexecutar a checagem de aniversários várias
# vezes no mesmo dia (a task do scheduler também dispara a verificação).
_ULTIMA_VERIFICACAO_ANIVERSARIO: Optional[date] = None


def is_privilegiado(posicao: str, nivel_acesso: str) -> bool:
    """Gerência, Sócio, Coordenador ou Admin podem criar eventos."""
    import unicodedata

    if (nivel_acesso or "").strip() == "Admin":
        return True
    pos = unicodedata.normalize("NFC", (posicao or "").strip().lower())
    permitidas = {"gerência", "sócio", "coordenador"}
    return pos in {unicodedata.normalize("NFC", p) for p in permitidas}


def is_gestao_feed(posicao: str, nivel_acesso: str) -> bool:
    """Gerência, Sócio ou Admin podem fixar/excluir posts de terceiros."""
    import unicodedata

    if (nivel_acesso or "").strip() == "Admin":
        return True
    pos = unicodedata.normalize("NFC", (posicao or "").strip().lower())
    permitidas = {"gerência", "sócio"}
    return pos in {unicodedata.normalize("NFC", p) for p in permitidas}


class FeedService:
    def __init__(self, db: Session):
        self.db = db

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _agora() -> datetime:
        """Agora em America/Sao_Paulo (naive, para comparação com o banco)."""
        return datetime.now(TZ).replace(tzinfo=None)

    def _autores(self, emails: List[str]) -> Dict[str, Investidor]:
        emails = [e for e in set(emails) if e]
        if not emails:
            return {}
        rows = self.db.execute(
            select(Investidor).where(Investidor.email.in_(emails))
        ).scalars().all()
        return {i.email: i for i in rows}

    @staticmethod
    def _autor_dict(inv: Optional[Investidor]) -> Dict[str, Any]:
        if not inv:
            return {"nome": "HUB Lisboa&CO", "profile_picture": None, "funcao": None}
        return {
            "nome": inv.nome or "Usuário",
            "profile_picture": inv.profile_picture,
            "funcao": inv.funcao or inv.posicao,
        }

    def _post_base(self) -> Any:
        agora = self._agora()
        return case(
            (
                and_(
                    FeedPost.fixado.is_(True),
                    or_(FeedPost.fixado_ate.is_(None), FeedPost.fixado_ate > agora),
                ),
                1,
            ),
            else_=0,
        )

    # ── Listagem ──────────────────────────────────────────────────────────────

    def listar_posts(
        self, usuario_email: str, pagina: int = 1, por_pagina: int = 10
    ) -> Dict[str, Any]:
        self.verificar_aniversarios()

        pagina = max(1, int(pagina or 1))
        offset = (pagina - 1) * por_pagina

        stmt = (
            select(FeedPost)
            .where(FeedPost.deletado.is_(False))
            .order_by(self._post_base().desc(), FeedPost.criado_em.desc())
            .offset(offset)
            .limit(por_pagina + 1)
        )
        posts = list(self.db.execute(stmt).scalars().all())
        tem_mais = len(posts) > por_pagina
        posts = posts[:por_pagina]

        return {
            "posts": self._serializar(posts, usuario_email),
            "tem_mais": tem_mais,
            "pagina": pagina,
        }

    def _serializar(
        self, posts: List[FeedPost], usuario_email: str
    ) -> List[Dict[str, Any]]:
        if not posts:
            return []
        ids = [p.id for p in posts]

        reac = self.db.execute(
            select(FeedReacao.post_id, FeedReacao.tipo, func.count())
            .where(FeedReacao.post_id.in_(ids))
            .group_by(FeedReacao.post_id, FeedReacao.tipo)
        ).all()
        reacoes_map: Dict[int, Dict[str, int]] = {}
        for post_id, tipo, qtd in reac:
            reacoes_map.setdefault(post_id, {})[tipo] = qtd

        minhas_rows = self.db.execute(
            select(FeedReacao.post_id, FeedReacao.tipo).where(
                FeedReacao.post_id.in_(ids),
                FeedReacao.usuario_email == usuario_email,
            )
        ).all()
        minhas = {post_id: tipo for post_id, tipo in minhas_rows}

        coment_rows = self.db.execute(
            select(FeedComentario.post_id, func.count())
            .where(
                FeedComentario.post_id.in_(ids),
                FeedComentario.deletado.is_(False),
            )
            .group_by(FeedComentario.post_id)
        ).all()
        coment_map = {post_id: qtd for post_id, qtd in coment_rows}

        autores = self._autores([p.autor_email for p in posts])

        resultado = []
        for p in posts:
            contagem = reacoes_map.get(p.id, {})
            resultado.append(
                {
                    "id": p.id,
                    "tipo": p.tipo,
                    "titulo": p.titulo,
                    "conteudo": p.conteudo,
                    "evento_data": p.evento_data.isoformat() if p.evento_data else None,
                    "evento_local": p.evento_local,
                    "fixado": bool(p.fixado),
                    "fixado_ate": p.fixado_ate.isoformat() if p.fixado_ate else None,
                    "criado_em": p.criado_em.isoformat() if p.criado_em else None,
                    "autor_email": p.autor_email,
                    "autor": self._autor_dict(autores.get(p.autor_email)),
                    "reacoes": contagem,
                    "total_reacoes": sum(contagem.values()),
                    "minha_reacao": minhas.get(p.id),
                    "total_comentarios": coment_map.get(p.id, 0),
                }
            )
        return resultado

    # ── Criação ───────────────────────────────────────────────────────────────

    def criar_post(self, autor_email: str, conteudo: str) -> Dict[str, Any]:
        conteudo = (conteudo or "").strip()
        if not conteudo:
            raise ValueError("O conteúdo do post não pode ser vazio.")

        post = FeedPost(
            autor_email=autor_email,
            tipo="post",
            conteudo=conteudo,
            criado_em=self._agora(),
        )
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        return self._serializar([post], autor_email)[0]

    def criar_evento(
        self,
        autor_email: str,
        titulo: str,
        conteudo: str,
        evento_data: Optional[datetime],
        evento_local: Optional[str],
        dias_fixado: int,
    ) -> Dict[str, Any]:
        titulo = (titulo or "").strip()
        if not titulo:
            raise ValueError("O evento precisa de um título.")

        agora = self._agora()
        dias = max(1, int(dias_fixado or 1))
        post = FeedPost(
            autor_email=autor_email,
            tipo="evento",
            titulo=titulo,
            conteudo=(conteudo or "").strip() or None,
            evento_data=evento_data,
            evento_local=(evento_local or "").strip() or None,
            fixado=True,
            fixado_ate=agora + timedelta(days=dias),
            criado_em=agora,
        )
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        return self._serializar([post], autor_email)[0]

    # ── Reações ───────────────────────────────────────────────────────────────

    def reagir(self, post_id: int, usuario_email: str, tipo: str) -> Dict[str, Any]:
        if tipo not in REACOES_VALIDAS:
            raise ValueError("Tipo de reação inválido.")

        post = self.db.get(FeedPost, post_id)
        if not post or post.deletado:
            raise ValueError("Post não encontrado.")

        existente = self.db.execute(
            select(FeedReacao).where(
                FeedReacao.post_id == post_id,
                FeedReacao.usuario_email == usuario_email,
            )
        ).scalar_one_or_none()

        if existente:
            if existente.tipo == tipo:
                self.db.delete(existente)
            else:
                existente.tipo = tipo
        else:
            self.db.add(
                FeedReacao(
                    post_id=post_id,
                    usuario_email=usuario_email,
                    tipo=tipo,
                    criado_em=self._agora(),
                )
            )
        self.db.commit()

        contagem = self.db.execute(
            select(FeedReacao.tipo, func.count())
            .where(FeedReacao.post_id == post_id)
            .group_by(FeedReacao.tipo)
        ).all()
        minha = self.db.execute(
            select(FeedReacao.tipo).where(
                FeedReacao.post_id == post_id,
                FeedReacao.usuario_email == usuario_email,
            )
        ).scalar_one_or_none()
        mapa = {t: q for t, q in contagem}
        return {
            "reacoes": mapa,
            "total_reacoes": sum(mapa.values()),
            "minha_reacao": minha,
        }

    # ── Comentários ───────────────────────────────────────────────────────────

    def listar_comentarios(self, post_id: int) -> List[Dict[str, Any]]:
        rows = list(
            self.db.execute(
                select(FeedComentario)
                .where(FeedComentario.post_id == post_id)
                .order_by(FeedComentario.criado_em.asc())
            ).scalars().all()
        )
        autores = self._autores([c.autor_email for c in rows])

        itens: Dict[int, Dict[str, Any]] = {}
        for c in rows:
            itens[c.id] = {
                "id": c.id,
                "post_id": c.post_id,
                "parent_id": c.parent_id,
                "conteudo": None if c.deletado else c.conteudo,
                "deletado": bool(c.deletado),
                "criado_em": c.criado_em.isoformat() if c.criado_em else None,
                "autor_email": c.autor_email,
                "autor": self._autor_dict(autores.get(c.autor_email)),
                "respostas": [],
            }

        raiz: List[Dict[str, Any]] = []
        for c in rows:
            item = itens[c.id]
            if c.parent_id and c.parent_id in itens:
                itens[c.parent_id]["respostas"].append(item)
            else:
                raiz.append(item)
        return raiz

    def comentar(
        self,
        post_id: int,
        autor_email: str,
        conteudo: str,
        parent_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        conteudo = (conteudo or "").strip()
        if not conteudo:
            raise ValueError("O comentário não pode ser vazio.")

        post = self.db.get(FeedPost, post_id)
        if not post or post.deletado:
            raise ValueError("Post não encontrado.")

        if parent_id:
            parent = self.db.get(FeedComentario, parent_id)
            if not parent or parent.post_id != post_id:
                raise ValueError("Comentário pai inválido.")

        comentario = FeedComentario(
            post_id=post_id,
            parent_id=parent_id,
            autor_email=autor_email,
            conteudo=conteudo,
            criado_em=self._agora(),
        )
        self.db.add(comentario)
        self.db.commit()
        self.db.refresh(comentario)

        autores = self._autores([autor_email])
        return {
            "id": comentario.id,
            "post_id": comentario.post_id,
            "parent_id": comentario.parent_id,
            "conteudo": comentario.conteudo,
            "deletado": False,
            "criado_em": comentario.criado_em.isoformat() if comentario.criado_em else None,
            "autor_email": autor_email,
            "autor": self._autor_dict(autores.get(autor_email)),
            "respostas": [],
        }

    # ── Fixação e remoção ─────────────────────────────────────────────────────

    def fixar_post(self, post_id: int, solicitante_email: str, gestao: bool, dias: int) -> None:
        post = self.db.get(FeedPost, post_id)
        if not post or post.deletado:
            raise ValueError("Post não encontrado.")
        if post.autor_email != solicitante_email and not gestao:
            raise PermissionError("Sem permissão para fixar este post.")
        dias = max(1, int(dias or 1))
        post.fixado = True
        post.fixado_ate = self._agora() + timedelta(days=dias)
        post.atualizado_em = self._agora()
        self.db.commit()

    def desfixar_post(self, post_id: int, solicitante_email: str, gestao: bool) -> None:
        post = self.db.get(FeedPost, post_id)
        if not post or post.deletado:
            raise ValueError("Post não encontrado.")
        if post.autor_email != solicitante_email and not gestao:
            raise PermissionError("Sem permissão para desfixar este post.")
        post.fixado = False
        post.fixado_ate = None
        post.atualizado_em = self._agora()
        self.db.commit()

    def deletar_post(self, post_id: int, solicitante_email: str, gestao: bool) -> None:
        post = self.db.get(FeedPost, post_id)
        if not post or post.deletado:
            raise ValueError("Post não encontrado.")
        if post.autor_email != solicitante_email and not gestao:
            raise PermissionError("Sem permissão para remover este post.")
        post.deletado = True
        post.atualizado_em = self._agora()
        self.db.commit()

    def deletar_comentario(
        self, comentario_id: int, solicitante_email: str, gestao: bool
    ) -> None:
        comentario = self.db.get(FeedComentario, comentario_id)
        if not comentario or comentario.deletado:
            raise ValueError("Comentário não encontrado.")
        if comentario.autor_email != solicitante_email and not gestao:
            raise PermissionError("Sem permissão para remover este comentário.")
        comentario.deletado = True
        self.db.commit()

    # ── Aniversários ──────────────────────────────────────────────────────────

    def verificar_aniversarios(self, forcar: bool = False) -> int:
        global _ULTIMA_VERIFICACAO_ANIVERSARIO
        hoje = self._agora().date()
        if not forcar and _ULTIMA_VERIFICACAO_ANIVERSARIO == hoje:
            return 0

        criados = 0
        hoje_inicio = datetime.combine(hoje, time.min)
        hoje_fim = hoje_inicio + timedelta(days=1)

        aniversariantes = self.db.execute(
            select(Investidor).where(
                Investidor.data_nascimento.isnot(None),
                Investidor.ativo.is_(True),
                func.extract("month", Investidor.data_nascimento) == hoje.month,
                func.extract("day", Investidor.data_nascimento) == hoje.day,
            )
        ).scalars().all()

        for inv in aniversariantes:
            ja_existe = self.db.execute(
                select(FeedPost.id).where(
                    FeedPost.tipo == "aniversario",
                    FeedPost.autor_email == inv.email,
                    FeedPost.criado_em >= hoje_inicio,
                    FeedPost.criado_em < hoje_fim,
                )
            ).first()
            if ja_existe:
                continue

            idade = hoje.year - inv.data_nascimento.year
            primeiro_nome = (inv.nome or "Colega").split(" ")[0]
            nome_completo = inv.nome or "Um colega"
            conteudo = (
                f"🎉 Hoje é aniversário de {nome_completo}! "
                f"{primeiro_nome} completa {idade} anos. Parabéns! 🎂"
            )

            self.db.add(
                FeedPost(
                    autor_email=inv.email,
                    tipo="aniversario",
                    conteudo=conteudo,
                    fixado=True,
                    fixado_ate=hoje_fim,
                    criado_em=self._agora(),
                )
            )
            criados += 1

        if criados:
            self.db.commit()

        _ULTIMA_VERIFICACAO_ANIVERSARIO = hoje
        return criados

    # ── Widgets ───────────────────────────────────────────────────────────────

    def aniversariantes_do_dia(self) -> List[Dict[str, Any]]:
        hoje = self._agora().date()
        rows = self.db.execute(
            select(Investidor)
            .where(
                Investidor.data_nascimento.isnot(None),
                Investidor.ativo.is_(True),
                func.extract("month", Investidor.data_nascimento) == hoje.month,
                func.extract("day", Investidor.data_nascimento) == hoje.day,
            )
            .order_by(Investidor.nome.asc())
        ).scalars().all()
        return [
            {
                "email": i.email,
                "nome": i.nome,
                "profile_picture": i.profile_picture,
                "funcao": i.funcao or i.posicao,
                "idade": hoje.year - i.data_nascimento.year,
            }
            for i in rows
        ]

    def proximos_eventos(self, limite: int = 5) -> List[Dict[str, Any]]:
        agora = self._agora()
        rows = self.db.execute(
            select(FeedPost)
            .where(
                FeedPost.tipo == "evento",
                FeedPost.deletado.is_(False),
                FeedPost.evento_data.isnot(None),
                FeedPost.evento_data >= agora,
            )
            .order_by(FeedPost.evento_data.asc())
            .limit(limite)
        ).scalars().all()
        autores = self._autores([p.autor_email for p in rows])
        return [
            {
                "id": p.id,
                "titulo": p.titulo,
                "evento_data": p.evento_data.isoformat() if p.evento_data else None,
                "evento_local": p.evento_local,
                "autor": self._autor_dict(autores.get(p.autor_email)),
            }
            for p in rows
        ]

    def em_alta(self, limite: int = 3, dias: int = 7) -> List[Dict[str, Any]]:
        desde = self._agora() - timedelta(days=dias)
        rows = self.db.execute(
            select(FeedPost, func.count(FeedReacao.id).label("total"))
            .join(FeedReacao, FeedReacao.post_id == FeedPost.id)
            .where(FeedPost.deletado.is_(False), FeedPost.criado_em >= desde)
            .group_by(FeedPost.id)
            .order_by(func.count(FeedReacao.id).desc(), FeedPost.criado_em.desc())
            .limit(limite)
        ).all()
        autores = self._autores([p.autor_email for p, _ in rows])
        return [
            {
                "id": p.id,
                "titulo": p.titulo,
                "tipo": p.tipo,
                "conteudo": (p.conteudo or "")[:120],
                "total_reacoes": total,
                "criado_em": p.criado_em.isoformat() if p.criado_em else None,
                "autor": self._autor_dict(autores.get(p.autor_email)),
            }
            for p, total in rows
        ]

    def ranking_participacao(self, limite: int = 5, dias: int = 7) -> List[Dict[str, Any]]:
        desde = self._agora() - timedelta(days=dias)

        posts_por = dict(
            self.db.execute(
                select(FeedPost.autor_email, func.count())
                .where(
                    FeedPost.deletado.is_(False),
                    FeedPost.criado_em >= desde,
                    FeedPost.autor_email.isnot(None),
                )
                .group_by(FeedPost.autor_email)
            ).all()
        )
        reac_por = dict(
            self.db.execute(
                select(FeedReacao.usuario_email, func.count())
                .where(FeedReacao.criado_em >= desde)
                .group_by(FeedReacao.usuario_email)
            ).all()
        )
        coment_por = dict(
            self.db.execute(
                select(FeedComentario.autor_email, func.count())
                .where(
                    FeedComentario.deletado.is_(False),
                    FeedComentario.criado_em >= desde,
                )
                .group_by(FeedComentario.autor_email)
            ).all()
        )

        emails = set(posts_por) | set(reac_por) | set(coment_por)
        autores = self._autores(list(emails))

        itens = []
        for email in emails:
            inv = autores.get(email)
            posts = posts_por.get(email, 0)
            reacoes = reac_por.get(email, 0)
            comentarios = coment_por.get(email, 0)
            itens.append(
                {
                    "email": email,
                    "nome": inv.nome if inv else email,
                    "profile_picture": inv.profile_picture if inv else None,
                    "posts": posts,
                    "reacoes": reacoes,
                    "comentarios": comentarios,
                    "total": posts + reacoes + comentarios,
                }
            )
        itens.sort(key=lambda x: x["total"], reverse=True)
        return itens[:limite]
