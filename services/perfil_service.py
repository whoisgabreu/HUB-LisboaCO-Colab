from datetime import date, datetime, time, timedelta

from models import Investidor, InvestidorProjeto, Projeto
from services.currency import CurrencyService
from feed.models import FeedPost, FeedReacao


def _so_digitos(valor, limite=None):
    if not valor:
        return None
    d = "".join(ch for ch in str(valor) if ch.isdigit())
    if not d:
        return None
    return d[:limite] if limite else d


def _parse_data(s):
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _tempo_casa(data_admissao):
    if not data_admissao:
        return None
    d = data_admissao.date() if hasattr(data_admissao, "date") else data_admissao
    dias = max(0, (date.today() - d).days)
    return {"dias": dias, "anos": dias // 365, "meses": (dias % 365) // 30}


def _ranking(db):
    """Ranking por clientes ativos + MRR (mesma regra do /api/ranking)."""
    projetos = {p.pipefy_id: p for p in db.query(Projeto).all()}
    invs = {i.email: i for i in db.query(Investidor).filter_by(ativo=True).all()}
    links = db.query(
        InvestidorProjeto.email_investidor,
        InvestidorProjeto.pipefy_id_projeto,
        InvestidorProjeto.active,
    ).all()
    rate = float(CurrencyService.get_usd_to_brl_rate())

    agg = {}
    for r in links:
        if r.email_investidor not in invs:
            continue
        a = agg.setdefault(r.email_investidor, {"clientsCount": 0, "mrr": 0.0})
        if r.active:
            a["clientsCount"] += 1
            p = projetos.get(r.pipefy_id_projeto)
            if p and p.fee is not None:
                fee = float(p.fee)
                if (p.moeda or "").strip().upper() == "USD":
                    fee *= rate
                a["mrr"] += fee

    ranking = [{"email": e, **v} for e, v in agg.items()]
    ranking.sort(key=lambda x: (-x["clientsCount"], -x["mrr"]))
    return ranking


def resumo_perfil(db, email):
    inv = db.query(Investidor).filter_by(email=email).first()
    if not inv:
        return None

    ranking = _ranking(db)
    projetos_ativos = 0
    posicao = None
    for i, r in enumerate(ranking):
        if r["email"] == email:
            projetos_ativos = r["clientsCount"]
            posicao = i + 1
            break

    return {
        "nome": inv.nome,
        "email": email,
        "funcao": inv.funcao or inv.posicao or "Colaborador",
        "telefone": inv.telefone or "",
        "profile_picture": inv.profile_picture or None,
        "data_nascimento": inv.data_nascimento.isoformat() if inv.data_nascimento else None,
        "data_admissao": inv.data_admissao.isoformat() if inv.data_admissao else None,
        "tempo_casa": _tempo_casa(inv.data_admissao),
        "projetos_ativos": projetos_ativos,
        "posicao_ranking": posicao,
        "ranking_total": len(ranking),
    }


def atividade_semanal(db, email, semanas=8):
    """Série semanal de atividade do usuário: postagens criadas e reações recebidas."""
    hoje = date.today()
    inicio_semana_atual = hoje - timedelta(days=hoje.weekday())
    primeira = inicio_semana_atual - timedelta(weeks=semanas - 1)
    desde_dt = datetime.combine(primeira, time.min)

    posts = db.query(FeedPost.id, FeedPost.criado_em).filter(
        FeedPost.autor_email == email,
        FeedPost.deletado.is_(False),
        FeedPost.criado_em >= desde_dt,
    ).all()
    post_ids = [p.id for p in posts]

    reacoes = []
    if post_ids:
        reacoes = db.query(FeedReacao.criado_em).filter(
            FeedReacao.post_id.in_(post_ids),
            FeedReacao.criado_em >= desde_dt,
        ).all()

    def chave(dt_val):
        if not dt_val:
            return None
        d = dt_val.date() if hasattr(dt_val, "date") else dt_val
        return d - timedelta(days=d.weekday())

    buckets = {}
    labels = []
    for i in range(semanas):
        sem = primeira + timedelta(weeks=i)
        buckets[sem] = {"posts": 0, "reacoes": 0}
        labels.append(sem.strftime("%d/%m"))

    for p in posts:
        k = chave(p.criado_em)
        if k in buckets:
            buckets[k]["posts"] += 1
    for r in reacoes:
        k = chave(r.criado_em)
        if k in buckets:
            buckets[k]["reacoes"] += 1

    semanas_ord = [primeira + timedelta(weeks=i) for i in range(semanas)]
    return {
        "labels": labels,
        "posts": [buckets[s]["posts"] for s in semanas_ord],
        "reacoes": [buckets[s]["reacoes"] for s in semanas_ord],
    }


def atualizar_perfil(db, email, dados):
    inv = db.query(Investidor).filter_by(email=email).first()
    if not inv:
        return None
    if "funcao" in dados and dados.get("funcao") is not None:
        inv.funcao = str(dados.get("funcao")).strip()[:50] or None
    if "telefone" in dados:
        inv.telefone = _so_digitos(dados.get("telefone"), 15)
    if "data_nascimento" in dados:
        dn = _parse_data(dados.get("data_nascimento"))
        if dn and dn > date.today():
            raise ValueError("Data de nascimento não pode ser no futuro.")
        inv.data_nascimento = dn
    db.commit()
    return resumo_perfil(db, email)