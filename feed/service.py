"""Serviço isolado do Feed social do HUB.

Responsável por posts, reações, comentários, enquetes, salvos, repost,
notificações, moderação, widgets e pelo post automático de aniversário.
Não altera services existentes.
"""

import html as html_lib
import re
from datetime import datetime, date, time, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, false, func, not_, or_, select
from sqlalchemy.orm import Session

from models import Investidor, InvestidorProjeto
from feed.models import (
    FeedComentario,
    FeedComentarioReacao,
    FeedDenuncia,
    FeedEnqueteVoto,
    FeedNotificacao,
    FeedPost,
    FeedPostEdicao,
    FeedReacao,
    FeedSalvo,
)

TZ = ZoneInfo("America/Sao_Paulo")

REACOES_VALIDAS = ["like", "love", "haha", "wow", "sad", "angry"]
VISIBILIDADES_VALIDAS = ["todos", "squad", "gestao"]
TIPOS_VALIDOS = ["post", "evento", "aniversario", "enquete", "repost"]

_URL_RE = re.compile(r"(https?://[^\s<]+)")
_MENCAO_RE = re.compile(r"@([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})")

# Cache em memória: evita reexecutar a checagem de aniversários várias
# vezes no mesmo dia (a task do scheduler também dispara a verificação).
_ULTIMA_VERIFICACAO_ANIVERSARIO: Optional[date] = None


def _normaliza_posicao(valor: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFC", (valor or "").strip().lower())


def is_privilegiado(posicao: str, nivel_acesso: str) -> bool:
    """Gerência, Sócio, Coordenador ou Admin podem criar eventos."""
    if (nivel_acesso or "").strip() == "Admin":
        return True
    permitidas = {"gerência", "sócio", "coordenador"}
    return _normaliza_posicao(posicao) in {_normaliza_posicao(p) for p in permitidas}


def is_gestao_feed(posicao: str, nivel_acesso: str) -> bool:
    """Gerência, Sócio ou Admin podem fixar/excluir/ocultar posts de terceiros."""
    if (nivel_acesso or "").strip() == "Admin":
        return True
    permitidas = {"gerência", "sócio"}
    return _normaliza_posicao(posicao) in {_normaliza_posicao(p) for p in permitidas}


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

    @staticmethod
    def _primeiro_nome(nome: str) -> str:
        return (nome or "Usuário").split(" ")[0]

    def _render_conteudo(self, texto: str, autores: Dict[str, Investidor]) -> Optional[str]:
        """Escapa, linka URLs e destaca @menções (seguro contra XSS)."""
        if not texto:
            return None
        out = html_lib.escape(texto)
        out = _URL_RE.sub(r'<a href="\1" target="_blank" rel="noopener">\1</a>', out)

        def _sub(m):
            email = m.group(1)
            inv = autores.get(email)
            nome = self._primeiro_nome(inv.nome) if inv else email.split("@")[0]
            return f'<span class="feed-mention">@{html_lib.escape(nome)}</span>'

        out = _MENCAO_RE.sub(_sub, out)
        return out.replace("\n", "<br>")

    @staticmethod
    def _emails_mencionados(texto: str) -> List[str]:
        if not texto:
            return []
        return list({m.group(1) for m in _MENCAO_RE.finditer(texto)})

    def _squad_emails(self, squad: str) -> List[str]:
        if not squad:
            return []
        rows = self.db.execute(
            select(Investidor.email).where(Investidor.squad == squad)
        ).scalars().all()
        return [e for e in rows if e]

    def _visibilidade_clause(self, usuario_email: str, gestao: bool, squad: str):
        """Retorna condição SQL de visibilidade ou None (gestão vê tudo)."""
        if gestao:
            return None
        branches = [
            FeedPost.visibilidade == "todos",
            FeedPost.autor_email == usuario_email,
        ]
        emails = self._squad_emails(squad)
        if emails:
            branches.append(
                and_(
                    FeedPost.visibilidade == "squad",
                    FeedPost.autor_email.in_(emails),
                )
            )
        return or_(*branches)

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

    def _pinned_activo(self):
        agora = self._agora()
        return and_(
            FeedPost.fixado.is_(True),
            or_(FeedPost.fixado_ate.is_(None), FeedPost.fixado_ate > agora),
        )

    def _condicoes_base(
        self,
        usuario_email: str,
        gestao: bool,
        squad: str,
        q: Optional[str] = None,
        tipo: Optional[str] = None,
        autor: Optional[str] = None,
        salvos: bool = False,
    ) -> List[Any]:
        conds: List[Any] = [FeedPost.deletado.is_(False)]
        if not gestao:
            conds.append(FeedPost.oculto.is_(False))
        vis = self._visibilidade_clause(usuario_email, gestao, squad)
        if vis is not None:
            conds.append(vis)
        if q:
            like = f"%{q}%"
            conds.append(or_(FeedPost.conteudo.ilike(like), FeedPost.titulo.ilike(like)))
        if tipo and tipo in TIPOS_VALIDOS:
            conds.append(FeedPost.tipo == tipo)
        if autor:
            conds.append(FeedPost.autor_email == autor)
        if salvos:
            conds.append(
                FeedPost.id.in_(
                    select(FeedSalvo.post_id).where(
                        FeedSalvo.usuario_email == usuario_email
                    )
                )
            )
        return conds

    # ── Listagem ──────────────────────────────────────────────────────────────

    def listar_posts(
        self,
        usuario_email: str,
        cursor: Optional[str] = None,
        por_pagina: int = 10,
        q: Optional[str] = None,
        tipo: Optional[str] = None,
        autor: Optional[str] = None,
        salvos: bool = False,
        posicao: str = "",
        nivel_acesso: str = "",
        squad: str = "",
    ) -> Dict[str, Any]:
        self.verificar_aniversarios()

        gestao = is_gestao_feed(posicao, nivel_acesso)
        conds = self._condicoes_base(usuario_email, gestao, squad, q, tipo, autor, salvos)

        posts: List[FeedPost] = []
        proximo_cursor = None

        # Página 1: fixados + primeira leva do stream
        if cursor is None:
            stmt_pin = (
                select(FeedPost)
                .where(*conds, self._pinned_activo())
                .order_by(FeedPost.criado_em.desc())
                .limit(5)
            )
            posts.extend(self.db.execute(stmt_pin).scalars().all())

        # Stream (não fixados ativos), ordenado por criado_em/id desc
        stream_conds = list(conds) + [not_(self._pinned_activo())]
        if cursor:
            ts, _, cid = cursor.partition("|")
            try:
                ts_dt = datetime.fromisoformat(ts)
                cid_int = int(cid)
            except (ValueError, TypeError):
                ts_dt, cid_int = None, None
            if ts_dt is not None:
                stream_conds.append(
                    or_(
                        FeedPost.criado_em < ts_dt,
                        and_(FeedPost.criado_em == ts_dt, FeedPost.id < cid_int),
                    )
                )

        stmt_stream = (
            select(FeedPost)
            .where(*stream_conds)
            .order_by(FeedPost.criado_em.desc(), FeedPost.id.desc())
            .limit(por_pagina + 1)
        )
        stream = list(self.db.execute(stmt_stream).scalars().all())
        tem_mais = len(stream) > por_pagina
        stream = stream[:por_pagina]

        if stream:
            ultimo = stream[-1]
            if ultimo.criado_em:
                proximo_cursor = f"{ultimo.criado_em.isoformat()}|{ultimo.id}"

        posts.extend(stream)

        return {
            "posts": self._serializar(posts, usuario_email),
            "tem_mais": tem_mais,
            "proximo_cursor": proximo_cursor,
        }

    def novos_posts(
        self,
        desde_iso: str,
        usuario_email: str,
        posicao: str = "",
        nivel_acesso: str = "",
        squad: str = "",
    ) -> Dict[str, Any]:
        gestao = is_gestao_feed(posicao, nivel_acesso)
        conds = self._condicoes_base(usuario_email, gestao, squad)
        if desde_iso:
            try:
                conds.append(FeedPost.criado_em > datetime.fromisoformat(desde_iso.replace("Z", "")))
            except ValueError:
                pass
        total = self.db.execute(
            select(func.count()).select_from(FeedPost).where(*conds)
        ).scalar()
        return {"total": int(total or 0)}

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

        salvos_rows = self.db.execute(
            select(FeedSalvo.post_id).where(
                FeedSalvo.post_id.in_(ids),
                FeedSalvo.usuario_email == usuario_email,
            )
        ).all()
        salvos = {r[0] for r in salvos_rows}

        # votos de enquetes
        enquete_ids = [p.id for p in posts if p.tipo == "enquete"]
        votos_map: Dict[int, Dict[int, int]] = {}
        meu_voto: Dict[int, int] = {}
        if enquete_ids:
            for post_id, opcao, qtd in self.db.execute(
                select(FeedEnqueteVoto.post_id, FeedEnqueteVoto.opcao_index, func.count())
                .where(FeedEnqueteVoto.post_id.in_(enquete_ids))
                .group_by(FeedEnqueteVoto.post_id, FeedEnqueteVoto.opcao_index)
            ).all():
                votos_map.setdefault(post_id, {})[opcao] = qtd
            for post_id, opcao in self.db.execute(
                select(FeedEnqueteVoto.post_id, FeedEnqueteVoto.opcao_index).where(
                    FeedEnqueteVoto.post_id.in_(enquete_ids),
                    FeedEnqueteVoto.usuario_email == usuario_email,
                )
            ).all():
                meu_voto[post_id] = opcao

        # reposts -> posts originais
        orig_ids = [p.original_post_id for p in posts if p.original_post_id]
        originais = {}
        if orig_ids:
            orig_rows = self.db.execute(
                select(FeedPost).where(FeedPost.id.in_(orig_ids))
            ).scalars().all()
            originais = {o.id: o for o in orig_rows}

        # autores + emails mencionados
        mencoes_emails = []
        for p in posts:
            mencoes_emails.extend(self._emails_mencionados(p.conteudo))
        autores = self._autores(
            [p.autor_email for p in posts]
            + mencoes_emails
            + [o.autor_email for o in originais.values()]
        )

        resultado = []
        for p in posts:
            contagem = reacoes_map.get(p.id, {})
            enquete = None
            if p.tipo == "enquete" and isinstance(p.enquete, dict):
                opcoes = p.enquete.get("opcoes", [])
                votos = votos_map.get(p.id, {})
                enquete = {
                    "opcoes": [
                        {"texto": o, "votos": votos.get(i, 0)} for i, o in enumerate(opcoes)
                    ],
                    "total": sum(votos.values()),
                    "minha_opcao": meu_voto.get(p.id),
                }

            original = None
            if p.tipo == "repost" and p.original_post_id in originais:
                o = originais[p.original_post_id]
                original = {
                    "id": o.id,
                    "tipo": o.tipo,
                    "titulo": o.titulo,
                    "conteudo": o.conteudo,
                    "conteudo_html": self._render_conteudo(o.conteudo, autores),
                    "criado_em": o.criado_em.isoformat() if o.criado_em else None,
                    "autor_email": o.autor_email,
                    "autor": self._autor_dict(autores.get(o.autor_email)),
                    "deletado": bool(o.deletado),
                }

            autor = self._autor_dict(autores.get(p.autor_email))
            resultado.append(
                {
                    "id": p.id,
                    "tipo": p.tipo,
                    "titulo": p.titulo,
                    "conteudo": p.conteudo,
                    "conteudo_html": self._render_conteudo(p.conteudo, autores),
                    "evento_data": p.evento_data.isoformat() if p.evento_data else None,
                    "evento_local": p.evento_local,
                    "fixado": bool(p.fixado),
                    "fixado_ate": p.fixado_ate.isoformat() if p.fixado_ate else None,
                    "criado_em": p.criado_em.isoformat() if p.criado_em else None,
                    "editado": bool(p.editado),
                    "total_edicoes": p.total_edicoes or 0,
                    "editado_em": p.editado_em.isoformat() if p.editado_em else None,
                    "visibilidade": p.visibilidade or "todos",
                    "oculto": bool(p.oculto),
                    "autor_email": p.autor_email,
                    "autor": autor,
                    "reacoes": contagem,
                    "total_reacoes": sum(contagem.values()),
                    "minha_reacao": minhas.get(p.id),
                    "total_comentarios": coment_map.get(p.id, 0),
                    "salvo": p.id in salvos,
                    "enquete": enquete,
                    "original": original,
                }
            )
        return resultado

    # ── Criação ───────────────────────────────────────────────────────────────

    def criar_post(
        self, autor_email: str, conteudo: str, visibilidade: str = "todos"
    ) -> Dict[str, Any]:
        conteudo = (conteudo or "").strip()
        if not conteudo:
            raise ValueError("O conteúdo do post não pode ser vazio.")
        if visibilidade not in VISIBILIDADES_VALIDAS:
            visibilidade = "todos"

        post = FeedPost(
            autor_email=autor_email,
            tipo="post",
            conteudo=conteudo,
            visibilidade=visibilidade,
            criado_em=self._agora(),
        )
        self.db.add(post)
        self.db.flush()
        self._notificar_mencoes(conteudo, autor_email, post.id)
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
        visibilidade: str = "todos",
    ) -> Dict[str, Any]:
        titulo = (titulo or "").strip()
        if not titulo:
            raise ValueError("O evento precisa de um título.")
        if visibilidade not in VISIBILIDADES_VALIDAS:
            visibilidade = "todos"

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
            visibilidade=visibilidade,
            criado_em=agora,
        )
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        return self._serializar([post], autor_email)[0]

    def criar_enquete(
        self,
        autor_email: str,
        pergunta: str,
        opcoes: List[str],
        visibilidade: str = "todos",
    ) -> Dict[str, Any]:
        pergunta = (pergunta or "").strip()
        opcoes = [str(o).strip() for o in (opcoes or []) if str(o).strip()]
        if not pergunta:
            raise ValueError("A enquete precisa de uma pergunta.")
        if len(opcoes) < 2:
            raise ValueError("A enquete precisa de pelo menos 2 opções.")
        if len(opcoes) > 6:
            raise ValueError("Máximo de 6 opções por enquete.")
        if visibilidade not in VISIBILIDADES_VALIDAS:
            visibilidade = "todos"

        post = FeedPost(
            autor_email=autor_email,
            tipo="enquete",
            conteudo=pergunta,
            enquete={"opcoes": opcoes},
            visibilidade=visibilidade,
            criado_em=self._agora(),
        )
        self.db.add(post)
        self.db.flush()
        self._notificar_mencoes(pergunta, autor_email, post.id)
        self.db.commit()
        self.db.refresh(post)
        return self._serializar([post], autor_email)[0]

    def repostar(
        self, post_id: int, autor_email: str, comentario: str = None, visibilidade: str = "todos"
    ) -> Dict[str, Any]:
        original = self.db.get(FeedPost, post_id)
        if not original or original.deletado:
            raise ValueError("Post não encontrado.")
        if visibilidade not in VISIBILIDADES_VALIDAS:
            visibilidade = "todos"
        post = FeedPost(
            autor_email=autor_email,
            tipo="repost",
            conteudo=(comentario or "").strip() or None,
            original_post_id=post_id,
            visibilidade=visibilidade,
            criado_em=self._agora(),
        )
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        return self._serializar([post], autor_email)[0]

    def editar_post(self, post_id: int, autor_email: str, novo_conteudo: str) -> Dict[str, Any]:
        novo_conteudo = (novo_conteudo or "").strip()
        if not novo_conteudo:
            raise ValueError("O conteúdo do post não pode ser vazio.")
        post = self.db.get(FeedPost, post_id)
        if not post or post.deletado:
            raise ValueError("Post não encontrado.")
        if post.autor_email != autor_email:
            raise PermissionError("Só o autor pode editar este post.")
        if post.tipo not in ("post", "enquete", "repost"):
            raise ValueError("Este tipo de publicação não pode ser editado.")

        self.db.add(
            FeedPostEdicao(
                post_id=post.id,
                conteudo_anterior=post.conteudo,
                editado_em=self._agora(),
                editado_por=autor_email,
            )
        )
        post.conteudo = novo_conteudo
        post.editado = True
        post.total_edicoes = (post.total_edicoes or 0) + 1
        post.editado_em = self._agora()
        post.atualizado_em = self._agora()
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
            self._notificar(post.autor_email, "reacao", usuario_email, post_id, None, "reagiu à sua publicação")
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

    def listar_comentarios(
        self, post_id: int, usuario_email: str = ""
    ) -> List[Dict[str, Any]]:
        rows = list(
            self.db.execute(
                select(FeedComentario)
                .where(FeedComentario.post_id == post_id)
                .order_by(FeedComentario.criado_em.asc())
            ).scalars().all()
        )
        ids = [c.id for c in rows]
        reac_map: Dict[int, Dict[str, int]] = {}
        minhas: Dict[int, str] = {}
        if ids:
            for cid, tipo, qtd in self.db.execute(
                select(FeedComentarioReacao.comentario_id, FeedComentarioReacao.tipo, func.count())
                .where(FeedComentarioReacao.comentario_id.in_(ids))
                .group_by(FeedComentarioReacao.comentario_id, FeedComentarioReacao.tipo)
            ).all():
                reac_map.setdefault(cid, {})[tipo] = qtd
            if usuario_email:
                for cid, tipo in self.db.execute(
                    select(FeedComentarioReacao.comentario_id, FeedComentarioReacao.tipo).where(
                        FeedComentarioReacao.comentario_id.in_(ids),
                        FeedComentarioReacao.usuario_email == usuario_email,
                    )
                ).all():
                    minhas[cid] = tipo

        mencoes = []
        for c in rows:
            mencoes.extend(self._emails_mencionados(c.conteudo))
        autores = self._autores([c.autor_email for c in rows] + mencoes)

        itens: Dict[int, Dict[str, Any]] = {}
        for c in rows:
            contagem = reac_map.get(c.id, {})
            itens[c.id] = {
                "id": c.id,
                "post_id": c.post_id,
                "parent_id": c.parent_id,
                "conteudo": None if c.deletado else c.conteudo,
                "conteudo_html": None if c.deletado else self._render_conteudo(c.conteudo, autores),
                "deletado": bool(c.deletado),
                "criado_em": c.criado_em.isoformat() if c.criado_em else None,
                "autor_email": c.autor_email,
                "autor": self._autor_dict(autores.get(c.autor_email)),
                "reacoes": contagem,
                "total_reacoes": sum(contagem.values()),
                "minha_reacao": minhas.get(c.id),
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

        parent = None
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
        self.db.flush()

        if parent:
            self._notificar(parent.autor_email, "resposta", autor_email, post_id, comentario.id, "respondeu seu comentário")
        self._notificar(post.autor_email, "comentario", autor_email, post_id, comentario.id, "comentou sua publicação")
        self._notificar_mencoes(conteudo, autor_email, post_id, comentario.id)
        self.db.commit()
        self.db.refresh(comentario)

        autores = self._autores([autor_email] + self._emails_mencionados(conteudo))
        return {
            "id": comentario.id,
            "post_id": comentario.post_id,
            "parent_id": comentario.parent_id,
            "conteudo": comentario.conteudo,
            "conteudo_html": self._render_conteudo(comentario.conteudo, autores),
            "deletado": False,
            "criado_em": comentario.criado_em.isoformat() if comentario.criado_em else None,
            "autor_email": autor_email,
            "autor": self._autor_dict(autores.get(autor_email)),
            "reacoes": {},
            "total_reacoes": 0,
            "minha_reacao": None,
            "respostas": [],
        }

    def reagir_comentario(self, comentario_id: int, usuario_email: str, tipo: str) -> Dict[str, Any]:
        if tipo not in REACOES_VALIDAS:
            raise ValueError("Tipo de reação inválido.")
        comentario = self.db.get(FeedComentario, comentario_id)
        if not comentario or comentario.deletado:
            raise ValueError("Comentário não encontrado.")

        existente = self.db.execute(
            select(FeedComentarioReacao).where(
                FeedComentarioReacao.comentario_id == comentario_id,
                FeedComentarioReacao.usuario_email == usuario_email,
            )
        ).scalar_one_or_none()
        if existente:
            if existente.tipo == tipo:
                self.db.delete(existente)
            else:
                existente.tipo = tipo
        else:
            self.db.add(
                FeedComentarioReacao(
                    comentario_id=comentario_id,
                    usuario_email=usuario_email,
                    tipo=tipo,
                    criado_em=self._agora(),
                )
            )
        self.db.commit()

        contagem = self.db.execute(
            select(FeedComentarioReacao.tipo, func.count())
            .where(FeedComentarioReacao.comentario_id == comentario_id)
            .group_by(FeedComentarioReacao.tipo)
        ).all()
        mapa = {t: q for t, q in contagem}
        minha = self.db.execute(
            select(FeedComentarioReacao.tipo).where(
                FeedComentarioReacao.comentario_id == comentario_id,
                FeedComentarioReacao.usuario_email == usuario_email,
            )
        ).scalar_one_or_none()
        return {"reacoes": mapa, "total_reacoes": sum(mapa.values()), "minha_reacao": minha}

    # ── Enquetes ──────────────────────────────────────────────────────────────

    def votar_enquete(self, post_id: int, usuario_email: str, opcao_index: int) -> Dict[str, Any]:
        post = self.db.get(FeedPost, post_id)
        if not post or post.deletado or post.tipo != "enquete" or not isinstance(post.enquete, dict):
            raise ValueError("Enquete não encontrada.")
        opcoes = post.enquete.get("opcoes", [])
        if not (0 <= int(opcao_index) < len(opcoes)):
            raise ValueError("Opção inválida.")

        existente = self.db.execute(
            select(FeedEnqueteVoto).where(
                FeedEnqueteVoto.post_id == post_id,
                FeedEnqueteVoto.usuario_email == usuario_email,
            )
        ).scalar_one_or_none()
        if existente:
            if existente.opcao_index == int(opcao_index):
                self.db.delete(existente)
            else:
                existente.opcao_index = int(opcao_index)
        else:
            self.db.add(
                FeedEnqueteVoto(
                    post_id=post_id,
                    usuario_email=usuario_email,
                    opcao_index=int(opcao_index),
                    criado_em=self._agora(),
                )
            )
        self.db.commit()

        votos = {}
        for idx, qtd in self.db.execute(
            select(FeedEnqueteVoto.opcao_index, func.count())
            .where(FeedEnqueteVoto.post_id == post_id)
            .group_by(FeedEnqueteVoto.opcao_index)
        ).all():
            votos[idx] = qtd
        meu = self.db.execute(
            select(FeedEnqueteVoto.opcao_index).where(
                FeedEnqueteVoto.post_id == post_id,
                FeedEnqueteVoto.usuario_email == usuario_email,
            )
        ).scalar_one_or_none()
        return {
            "opcoes": [{"texto": o, "votos": votos.get(i, 0)} for i, o in enumerate(opcoes)],
            "total": sum(votos.values()),
            "minha_opcao": meu,
        }

    # ── Salvos ────────────────────────────────────────────────────────────────

    def alternar_salvo(self, post_id: int, usuario_email: str) -> Dict[str, Any]:
        post = self.db.get(FeedPost, post_id)
        if not post or post.deletado:
            raise ValueError("Post não encontrado.")
        existente = self.db.execute(
            select(FeedSalvo).where(
                FeedSalvo.post_id == post_id,
                FeedSalvo.usuario_email == usuario_email,
            )
        ).scalar_one_or_none()
        if existente:
            self.db.delete(existente)
            salvo = False
        else:
            self.db.add(FeedSalvo(post_id=post_id, usuario_email=usuario_email, criado_em=self._agora()))
            salvo = True
        self.db.commit()
        return {"salvo": salvo}

    # ── Fixação, moderação e remoção ──────────────────────────────────────────

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

    def ocultar_post(self, post_id: int, ocultar: bool) -> None:
        post = self.db.get(FeedPost, post_id)
        if not post or post.deletado:
            raise ValueError("Post não encontrado.")
        post.oculto = bool(ocultar)
        post.atualizado_em = self._agora()
        self.db.commit()

    def denunciar_post(self, post_id: int, usuario_email: str, motivo: str) -> None:
        post = self.db.get(FeedPost, post_id)
        if not post or post.deletado:
            raise ValueError("Post não encontrado.")
        existente = self.db.execute(
            select(FeedDenuncia).where(
                FeedDenuncia.post_id == post_id,
                FeedDenuncia.usuario_email == usuario_email,
            )
        ).scalar_one_or_none()
        if existente:
            existente.motivo = (motivo or "").strip() or existente.motivo
        else:
            self.db.add(
                FeedDenuncia(
                    post_id=post_id,
                    usuario_email=usuario_email,
                    motivo=(motivo or "").strip() or None,
                    criado_em=self._agora(),
                )
            )
        self.db.commit()

    # ── Perfil ────────────────────────────────────────────────────────────────

    def perfil_usuario(self, email: str) -> Dict[str, Any]:
        inv = self.db.execute(
            select(Investidor).where(Investidor.email == email)
        ).scalar_one_or_none()
        if not inv:
            raise ValueError("Usuário não encontrado.")

        desde = self.db.execute(
            select(func.min(InvestidorProjeto.created_at)).where(
                InvestidorProjeto.email_investidor == email
            )
        ).scalar()
        ativos = self.db.execute(
            select(func.count())
            .select_from(InvestidorProjeto)
            .where(
                InvestidorProjeto.email_investidor == email,
                InvestidorProjeto.active.is_(True),
            )
        ).scalar()

        anos_casa = None
        if desde:
            hoje = self._agora().date()
            anos_casa = hoje.year - desde.year - ((hoje.month, hoje.day) < (desde.month, desde.day))

        return {
            "email": inv.email,
            "nome": inv.nome,
            "funcao": inv.funcao or inv.posicao,
            "posicao": inv.posicao,
            "squad": inv.squad,
            "senioridade": inv.senioridade,
            "profile_picture": inv.profile_picture,
            "data_nascimento": inv.data_nascimento.isoformat() if inv.data_nascimento else None,
            "tempo_de_casa": anos_casa,
            "clientes_ativos": int(ativos or 0),
        }

    def listar_usuarios_para_mencao(self) -> List[Dict[str, Any]]:
        rows = self.db.execute(
            select(Investidor)
            .where(Investidor.ativo.is_(True), Investidor.email.isnot(None))
            .order_by(Investidor.nome.asc())
        ).scalars().all()
        return [
            {
                "email": i.email,
                "nome": i.nome,
                "profile_picture": i.profile_picture,
                "squad": i.squad,
            }
            for i in rows
        ]

    # ── Notificações ──────────────────────────────────────────────────────────

    def _notificar(
        self,
        usuario_email: Optional[str],
        tipo: str,
        ator_email: Optional[str],
        post_id: Optional[int],
        comentario_id: Optional[int],
        texto: str,
    ) -> None:
        if not usuario_email or usuario_email == ator_email:
            return
        self.db.add(
            FeedNotificacao(
                usuario_email=usuario_email,
                tipo=tipo,
                ator_email=ator_email,
                post_id=post_id,
                comentario_id=comentario_id,
                texto=texto,
                lida=False,
                criado_em=self._agora(),
            )
        )

    def _notificar_mencoes(
        self,
        texto: str,
        ator_email: str,
        post_id: Optional[int] = None,
        comentario_id: Optional[int] = None,
    ) -> None:
        emails = self._emails_mencionados(texto)
        if not emails:
            return
        existentes = set(
            self.db.execute(
                select(Investidor.email).where(Investidor.email.in_(emails))
            ).scalars().all()
        )
        for email in existentes:
            self._notificar(email, "mencao", ator_email, post_id, comentario_id, "mencionou você")

    def listar_notificacoes(self, usuario_email: str, limite: int = 20) -> List[Dict[str, Any]]:
        rows = list(
            self.db.execute(
                select(FeedNotificacao)
                .where(FeedNotificacao.usuario_email == usuario_email)
                .order_by(FeedNotificacao.criado_em.desc())
                .limit(limite)
            ).scalars().all()
        )
        autores = self._autores([n.ator_email for n in rows])
        return [
            {
                "id": n.id,
                "tipo": n.tipo,
                "texto": n.texto,
                "post_id": n.post_id,
                "comentario_id": n.comentario_id,
                "lida": bool(n.lida),
                "criado_em": n.criado_em.isoformat() if n.criado_em else None,
                "ator_email": n.ator_email,
                "autor": self._autor_dict(autores.get(n.ator_email)),
            }
            for n in rows
        ]

    def contar_nao_lidas(self, usuario_email: str) -> int:
        total = self.db.execute(
            select(func.count())
            .select_from(FeedNotificacao)
            .where(
                FeedNotificacao.usuario_email == usuario_email,
                FeedNotificacao.lida.is_(False),
            )
        ).scalar()
        return int(total or 0)

    def marcar_lida(self, notificacao_id: int, usuario_email: str) -> None:
        n = self.db.get(FeedNotificacao, notificacao_id)
        if n and n.usuario_email == usuario_email:
            n.lida = True
            self.db.commit()

    def marcar_todas_lidas(self, usuario_email: str) -> None:
        for n in self.db.execute(
            select(FeedNotificacao).where(
                FeedNotificacao.usuario_email == usuario_email,
                FeedNotificacao.lida.is_(False),
            )
        ).scalars().all():
            n.lida = True
        self.db.commit()

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
