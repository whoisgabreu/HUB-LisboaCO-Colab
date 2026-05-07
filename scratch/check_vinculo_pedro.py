"""Verifica vinculos de pedro.vitorino e investidor data."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

EMAIL = "pedro.vitorino@v4company.com"

with engine.connect() as c:
    print(f"\n=== Investidor {EMAIL} ===")
    inv = c.execute(text(
        "SELECT email, funcao, posicao, senioridade, squad FROM plataforma_geral.investidores "
        "WHERE email = :e"
    ), {"e": EMAIL}).fetchone()
    if inv:
        print(f"  funcao={inv[1]} posicao={inv[2]} senioridade={inv[3]} squad={inv[4]}")

    print(f"\n=== Vínculos de {EMAIL} (mai/2026) ===")
    rows = c.execute(text(
        "SELECT v.pipefy_id_projeto, v.cientista, v.active, "
        "       COALESCE(p.nome, p2.nome) AS nome_proj "
        "FROM plataforma_geral.investidores_projetos v "
        "LEFT JOIN plataforma_geral.projetos_ativos p ON p.pipefy_id = v.pipefy_id_projeto "
        "LEFT JOIN plataforma_geral.projetos p2 ON p2.pipefy_id = v.pipefy_id_projeto "
        "WHERE v.email_investidor = :e "
        "ORDER BY v.pipefy_id_projeto"
    ), {"e": EMAIL}).fetchall()

    for r in rows:
        pid, cientista, active, nome = r
        flag = []
        if cientista: flag.append("CIENTISTA")
        if not active: flag.append("INATIVO")
        flag_str = f"[{', '.join(flag)}]" if flag else ""
        print(f"  {pid} | {(nome or '?')[:50]:<50} {flag_str}")
