"""Serviço isolado do Chat interno do HUB (1:1)."""

import html as html_lib
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from models import Investidor
from chat.models import ChatConversa, ChatLeitura, ChatMensagem, ChatPresenca

TZ = ZoneInfo("America/Sao_Paulo")
PRESENCA_TTL = 60  # segundos

_URL_RE = re.compile(r"(https?://[^\s<]+)")
_MENCAO_RE = re.compile(r"@([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})")


class ChatService:
    def __init__(self, db: Session):
        self.db = db

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _agora() -> datetime:
        return datetime.now(TZ).replace(tzinfo=None)

    @staticmethod
    def _par(a: str, b: str):
        return (a, b) if a <= b else (b, a)

    @staticmethod
    def _autor_dict(inv: Optional[Investidor]) -> Dict[str, Any]:
        if not inv:
            return {"nome": "Usuário", "profile_picture": None, "funcao": None}
        return {
            "nome": inv.nome or "Usuário",
            "profile_picture": inv.profile_picture,
            "funcao": inv.funcao or inv.posicao,
        }

    def _autores(self, emails: List[str]) -> Dict[str, Investidor]:
        emails = [e for e in set(emails) if e]
        if not emails:
            return {}
        rows = self.db.execute(
            select(Investidor).where(Investidor.email.in_(emails))
        ).scalars().all()
        return {i.email: i for i in rows}

    def _render_conteudo(self, texto: str, autores: Dict[str, Investidor]) -> Optional[str]:
        if not texto:
            return None
        out = html_lib.escape(texto)
        out = _URL_RE.sub(r'<a href="\1" target="_blank" rel="noopener">\1</a>', out)

        def _sub(m):
            email = m.group(1)
            inv = autores.get(email)
            nome = (inv.nome or email).split(" ")[0] if inv else email.split("@")[0]
            return f'<span class="chat-mention">@{html_lib.escape(nome)}</span>'

        out = _MENCAO_RE.sub(_sub, out)
        return out.replace("\n", "<br>")

    @staticmethod
    def _emails_mencionados(texto: str) -> List[str]:
        if not texto:
            return []
        return list({m.group(1) for m in _MENCAO_RE.finditer(texto)})

    def _online(self) -> set:
        limite = self._agora() - timedelta(seconds=PRESENCA_TTL)
        rows = self.db.execute(
            select(ChatPresenca.usuario_email).where(ChatPresenca.ultimo_ping >= limite)
        ).scalars().all()
        return set(rows)

    def _conversa_participante(self, conversa_id: int, usuario_email: str) -> ChatConversa:
        conv = self.db.get(ChatConversa, conversa_id)
        if not conv:
            raise ValueError("Conversa não encontrada.")
        if usuario_email not in (conv.user_a, conv.user_b):
            raise PermissionError("Sem acesso a esta conversa.")
        return conv

    @staticmethod
    def _outro(conv: ChatConversa, usuario_email: str) -> str:
        return conv.user_b if conv.user_a == usuario_email else conv.user_a

    def _conversa_por_par(self, a: str, b: str) -> Optional[ChatConversa]:
        ua, ub = self._par(a, b)
        return self.db.execute(
            select(ChatConversa).where(ChatConversa.user_a == ua, ChatConversa.user_b == ub)
        ).scalar_one_or_none()

    def _ler_map(self, usuario_email: str, conversa_ids: List[int]) -> Dict[int, int]:
        if not conversa_ids:
            return {}
        rows = self.db.execute(
            select(ChatLeitura.conversa_id, ChatLeitura.ultima_lida_msg_id).where(
                ChatLeitura.usuario_email == usuario_email,
                ChatLeitura.conversa_id.in_(conversa_ids),
            )
        ).all()
        return {cid: int(mid or 0) for cid, mid in rows}

    def _nao_lidas_map(self, usuario_email: str, convs: List[ChatConversa]) -> Dict[int, int]:
        if not convs:
            return {}
        ids = [c.id for c in convs]
        leituras = self._ler_map(usuario_email, ids)
        resultado = {}
        for c in convs:
            ultima = leituras.get(c.id, 0)
            total = self.db.execute(
                select(func.count())
                .select_from(ChatMensagem)
                .where(
                    ChatMensagem.conversa_id == c.id,
                    ChatMensagem.deletado.is_(False),
                    ChatMensagem.autor_email != usuario_email,
                    ChatMensagem.id > ultima,
                )
            ).scalar()
            resultado[c.id] = int(total or 0)
        return resultado

    # ── Conversas ─────────────────────────────────────────────────────────────

    def obter_ou_criar_conversa(self, usuario_email: str, outro_email: str) -> Dict[str, Any]:
        if not outro_email or outro_email == usuario_email:
            raise ValueError("Selecione outro usuário.")
        outro = self.db.execute(
            select(Investidor).where(Investidor.email == outro_email)
        ).scalar_one_or_none()
        if not outro:
            raise ValueError("Usuário não encontrado.")

        conv = self._conversa_por_par(usuario_email, outro_email)
        if not conv:
            ua, ub = self._par(usuario_email, outro_email)
            conv = ChatConversa(user_a=ua, user_b=ub, criado_em=self._agora())
            self.db.add(conv)
            self.db.commit()
            self.db.refresh(conv)
        return self._serializar_conversa(conv, usuario_email, self._online())

    def listar_conversas(self, usuario_email: str) -> List[Dict[str, Any]]:
        convs = list(
            self.db.execute(
                select(ChatConversa)
                .where(or_(ChatConversa.user_a == usuario_email, ChatConversa.user_b == usuario_email))
                .order_by(ChatConversa.ultima_mensagem_em.desc().nullslast(), ChatConversa.id.desc())
            ).scalars().all()
        )
        online = self._online()
        return [self._serializar_conversa(c, usuario_email, online) for c in convs]

    def _serializar_conversa(self, conv, usuario_email, online) -> Dict[str, Any]:
        outro_email = self._outro(conv, usuario_email)
        autores = self._autores([outro_email])
        last = self.db.execute(
            select(ChatMensagem)
            .where(ChatMensagem.conversa_id == conv.id)
            .order_by(ChatMensagem.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        ultima = None
        if last:
            ultima = {
                "conteudo": None if last.deletado else last.conteudo[:120],
                "autor_email": last.autor_email,
                "criado_em": last.criado_em.isoformat() if last.criado_em else None,
                "deletado": bool(last.deletado),
            }
        ler = self._ler_map(usuario_email, [conv.id]).get(conv.id, 0)
        nao_lidas = self.db.execute(
            select(func.count())
            .select_from(ChatMensagem)
            .where(
                ChatMensagem.conversa_id == conv.id,
                ChatMensagem.deletado.is_(False),
                ChatMensagem.autor_email != usuario_email,
                ChatMensagem.id > ler,
            )
        ).scalar()
        return {
            "id": conv.id,
            "outro_email": outro_email,
            "outro": self._autor_dict(autores.get(outro_email)),
            "online": outro_email in online,
            "ultima_mensagem": ultima,
            "ultima_mensagem_em": conv.ultima_mensagem_em.isoformat() if conv.ultima_mensagem_em else None,
            "nao_lidas": int(nao_lidas or 0),
        }

    # ── Pessoas ativas ────────────────────────────────────────────────────────

    def listar_usuarios_ativos(self, usuario_email: str) -> List[Dict[str, Any]]:
        rows = self.db.execute(
            select(Investidor)
            .where(Investidor.ativo.is_(True), Investidor.email.isnot(None), Investidor.email != usuario_email)
            .order_by(Investidor.nome.asc())
        ).scalars().all()
        online = self._online()
        # conversas existentes
        convs = list(
            self.db.execute(
                select(ChatConversa).where(
                    or_(ChatConversa.user_a == usuario_email, ChatConversa.user_b == usuario_email)
                )
            ).scalars().all()
        )
        conv_por_outro = {self._outro(c, usuario_email): c.id for c in convs}
        return [
            {
                "email": i.email,
                "nome": i.nome,
                "profile_picture": i.profile_picture,
                "funcao": i.funcao or i.posicao,
                "squad": i.squad,
                "online": i.email in online,
                "conversa_id": conv_por_outro.get(i.email),
            }
            for i in rows
        ]

    # ── Mensagens ─────────────────────────────────────────────────────────────

    def listar_mensagens(
        self, conversa_id: int, usuario_email: str, cursor: Optional[int] = None, por_pagina: int = 30
    ) -> Dict[str, Any]:
        conv = self._conversa_participante(conversa_id, usuario_email)
        outro_email = self._outro(conv, usuario_email)

        stmt = select(ChatMensagem).where(ChatMensagem.conversa_id == conversa_id)
        if cursor:
            stmt = stmt.where(ChatMensagem.id < int(cursor))
        stmt = stmt.order_by(ChatMensagem.id.desc()).limit(por_pagina + 1)
        rows = list(self.db.execute(stmt).scalars().all())
        tem_mais = len(rows) > por_pagina
        rows = rows[:por_pagina]
        rows.reverse()  # ordem cronológica

        # última leitura do outro (para ✓✓)
        outra_leitura = self.db.execute(
            select(ChatLeitura.ultima_lida_msg_id).where(
                ChatLeitura.conversa_id == conversa_id,
                ChatLeitura.usuario_email == outro_email,
            )
        ).scalar_one_or_none() or 0

        mencoes = []
        for m in rows:
            mencoes.extend(self._emails_mencionados(m.conteudo))
        autores = self._autores([m.autor_email for m in rows] + mencoes)

        proximo_cursor = rows[0].id if rows else None
        return {
            "mensagens": [
                self._serializar_mensagem(m, usuario_email, int(outra_leitura), autores) for m in rows
            ],
            "tem_mais": tem_mais,
            "cursor": proximo_cursor,
            "online": outro_email in self._online(),
            "outro": self._autor_dict(autores.get(outro_email)),
            "outro_email": outro_email,
        }

    def _serializar_mensagem(self, m, usuario_email, outra_leitura, autores=None) -> Dict[str, Any]:
        if autores is None:
            autores = self._autores([m.autor_email] + self._emails_mencionados(m.conteudo))
        meu = m.autor_email == usuario_email
        return {
            "id": m.id,
            "conversa_id": m.conversa_id,
            "autor_email": m.autor_email,
            "conteudo": None if m.deletado else m.conteudo,
            "conteudo_html": None if m.deletado else self._render_conteudo(m.conteudo, autores),
            "editado": bool(m.editado),
            "editado_em": m.editado_em.isoformat() if m.editado_em else None,
            "deletado": bool(m.deletado),
            "criado_em": m.criado_em.isoformat() if m.criado_em else None,
            "meu": meu,
            "lida": bool(meu and m.id <= outra_leitura),
        }

    def enviar_mensagem(self, conversa_id: int, autor_email: str, conteudo: str) -> Dict[str, Any]:
        conteudo = (conteudo or "").strip()
        if not conteudo:
            raise ValueError("A mensagem não pode ser vazia.")
        self._conversa_participante(conversa_id, autor_email)

        agora = self._agora()
        msg = ChatMensagem(
            conversa_id=conversa_id,
            autor_email=autor_email,
            conteudo=conteudo,
            criado_em=agora,
        )
        self.db.add(msg)
        conv = self.db.get(ChatConversa, conversa_id)
        conv.ultima_mensagem_em = agora
        self.db.commit()
        self.db.refresh(msg)

        # garante que o autor está em dia
        self.marcar_lida(conversa_id, autor_email)
        return self._serializar_mensagem(msg, autor_email, 0)

    def editar_mensagem(self, mensagem_id: int, autor_email: str, conteudo: str) -> Dict[str, Any]:
        conteudo = (conteudo or "").strip()
        if not conteudo:
            raise ValueError("A mensagem não pode ser vazia.")
        msg = self.db.get(ChatMensagem, mensagem_id)
        if not msg or msg.deletado:
            raise ValueError("Mensagem não encontrada.")
        if msg.autor_email != autor_email:
            raise PermissionError("Só o autor pode editar a mensagem.")
        msg.conteudo = conteudo
        msg.editado = True
        msg.editado_em = self._agora()
        self.db.commit()
        self.db.refresh(msg)
        return self._serializar_mensagem(msg, autor_email, 0)

    def deletar_mensagem(self, mensagem_id: int, autor_email: str) -> None:
        msg = self.db.get(ChatMensagem, mensagem_id)
        if not msg or msg.deletado:
            raise ValueError("Mensagem não encontrada.")
        if msg.autor_email != autor_email:
            raise PermissionError("Só o autor pode excluir a mensagem.")
        msg.deletado = True
        self.db.commit()

    # ── Leitura / não lidas ───────────────────────────────────────────────────

    def marcar_lida(self, conversa_id: int, usuario_email: str) -> None:
        conv = self._conversa_participante(conversa_id, usuario_email)
        ultimo = self.db.execute(
            select(func.max(ChatMensagem.id)).where(ChatMensagem.conversa_id == conv.id)
        ).scalar() or 0

        leitura = self.db.execute(
            select(ChatLeitura).where(
                ChatLeitura.conversa_id == conversa_id,
                ChatLeitura.usuario_email == usuario_email,
            )
        ).scalar_one_or_none()
        if leitura:
            if ultimo > (leitura.ultima_lida_msg_id or 0):
                leitura.ultima_lida_msg_id = ultimo
                leitura.ultima_lida_em = self._agora()
        else:
            self.db.add(
                ChatLeitura(
                    conversa_id=conversa_id,
                    usuario_email=usuario_email,
                    ultima_lida_msg_id=ultimo,
                    ultima_lida_em=self._agora(),
                )
            )
        self.db.commit()

    def total_nao_lidas(self, usuario_email: str) -> int:
        convs = list(
            self.db.execute(
                select(ChatConversa).where(
                    or_(ChatConversa.user_a == usuario_email, ChatConversa.user_b == usuario_email)
                )
            ).scalars().all()
        )
        return sum(self._nao_lidas_map(usuario_email, convs).values())

    def marcar_todas_lidas(self, usuario_email: str) -> None:
        convs = list(
            self.db.execute(
                select(ChatConversa).where(
                    or_(ChatConversa.user_a == usuario_email, ChatConversa.user_b == usuario_email)
                )
            ).scalars().all()
        )
        agora = self._agora()
        for conv in convs:
            ultimo = self.db.execute(
                select(func.max(ChatMensagem.id)).where(ChatMensagem.conversa_id == conv.id)
            ).scalar() or 0
            leitura = self.db.execute(
                select(ChatLeitura).where(
                    ChatLeitura.conversa_id == conv.id,
                    ChatLeitura.usuario_email == usuario_email,
                )
            ).scalar_one_or_none()
            if leitura:
                if ultimo > (leitura.ultima_lida_msg_id or 0):
                    leitura.ultima_lida_msg_id = ultimo
                    leitura.ultima_lida_em = agora
            else:
                self.db.add(
                    ChatLeitura(
                        conversa_id=conv.id,
                        usuario_email=usuario_email,
                        ultima_lida_msg_id=ultimo,
                        ultima_lida_em=agora,
                    )
                )
        self.db.commit()

    # ── Busca ─────────────────────────────────────────────────────────────────

    def buscar(self, usuario_email: str, q: str) -> Dict[str, Any]:
        """Busca por pessoas (nome/e-mail, todos ativos) e por mensagens."""
        q = (q or "").strip()
        if not q:
            return {"pessoas": [], "mensagens": []}
        like = f"%{q}%"

        # ── Pessoas (todos os usuários ativos, exceto o próprio) ──
        pessoas_rows = self.db.execute(
            select(Investidor)
            .where(
                Investidor.ativo.is_(True),
                Investidor.email.isnot(None),
                Investidor.email != usuario_email,
                or_(Investidor.nome.ilike(like), Investidor.email.ilike(like)),
            )
            .order_by(Investidor.nome.asc())
            .limit(10)
        ).scalars().all()

        emails_pessoas = [p.email for p in pessoas_rows]
        conv_por_outro = {}
        if emails_pessoas:
            convs = self.db.execute(
                select(ChatConversa).where(
                    or_(ChatConversa.user_a == usuario_email, ChatConversa.user_b == usuario_email)
                )
            ).scalars().all()
            for c in convs:
                outro = self._outro(c, usuario_email)
                if outro in emails_pessoas:
                    conv_por_outro[outro] = c.id

        online = self._online()
        pessoas = [
            {
                "email": p.email,
                "nome": p.nome,
                "profile_picture": p.profile_picture,
                "funcao": p.funcao or p.posicao,
                "squad": p.squad,
                "online": p.email in online,
                "conversa_id": conv_por_outro.get(p.email),
            }
            for p in pessoas_rows
        ]

        # ── Mensagens (conteúdo nas conversas do usuário) ──
        rows = self.db.execute(
            select(ChatMensagem)
            .join(ChatConversa, ChatConversa.id == ChatMensagem.conversa_id)
            .where(
                or_(ChatConversa.user_a == usuario_email, ChatConversa.user_b == usuario_email),
                ChatMensagem.deletado.is_(False),
                ChatMensagem.conteudo.ilike(like),
            )
            .order_by(ChatMensagem.id.desc())
            .limit(30)
        ).scalars().all()

        conv_ids = list({m.conversa_id for m in rows})
        convs = {
            c.id: c
            for c in self.db.execute(
                select(ChatConversa).where(ChatConversa.id.in_(conv_ids))
            ).scalars().all()
        }
        outros = [self._outro(convs[m.conversa_id], usuario_email) for m in rows if m.conversa_id in convs]
        autores = self._autores(outros)

        mensagens = [
            {
                "id": m.id,
                "conversa_id": m.conversa_id,
                "outro_email": self._outro(convs[m.conversa_id], usuario_email) if m.conversa_id in convs else None,
                "outro": self._autor_dict(autores.get(self._outro(convs[m.conversa_id], usuario_email))) if m.conversa_id in convs else None,
                "conteudo": m.conteudo,
                "conteudo_html": self._render_conteudo(m.conteudo, autores),
                "criado_em": m.criado_em.isoformat() if m.criado_em else None,
            }
            for m in rows
        ]

        return {"pessoas": pessoas, "mensagens": mensagens}

    # ── Presença ──────────────────────────────────────────────────────────────

    def ping(self, usuario_email: str) -> None:
        if not usuario_email:
            return
        p = self.db.get(ChatPresenca, usuario_email)
        if p:
            p.ultimo_ping = self._agora()
        else:
            self.db.add(ChatPresenca(usuario_email=usuario_email, ultimo_ping=self._agora()))
        self.db.commit()
