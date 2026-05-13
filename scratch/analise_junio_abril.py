"""Análise: lista de clientes/fees do investidor 'junio' em abril/2026."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

with engine.connect() as c:
    # Acha o investidor
    inv = c.execute(text(
        "SELECT email, nome, funcao, posicao, squad FROM plataforma_geral.investidores "
        "WHERE LOWER(nome) LIKE '%junio%' OR LOWER(email) LIKE '%junio%'"
    )).fetchall()
    print("\n=== Investidor 'junio' ===")
    for i in inv:
        print(f"  email={i[0]} nome={i[1]} funcao={i[2]} posicao={i[3]} squad={i[4]}")

    if not inv:
        print("  (não encontrado)")
        sys.exit(0)

    EMAIL = inv[0][0]
    print(f"\nUsando: {EMAIL}\n")

with engine.connect() as c:
    # Vinculos do investidor (todos, ativos e inativos)
    print(f"=== Vínculos de {EMAIL} ===")
    vinc = c.execute(text(
        "SELECT v.pipefy_id_projeto, v.cientista, v.active, v.inactivated_at, v.fee_projeto, "
        "       COALESCE(pa.nome, p.nome) AS nome_proj, "
        "       COALESCE(pa.fee, p.fee) AS fee_atual, "
        "       COALESCE(pa.moeda, p.moeda) AS moeda, "
        "       COALESCE(pa.fase_do_pipefy, p.fase_do_pipefy) AS fase "
        "FROM plataforma_geral.investidores_projetos v "
        "LEFT JOIN plataforma_geral.projetos_ativos pa ON pa.pipefy_id = v.pipefy_id_projeto "
        "LEFT JOIN plataforma_geral.projetos p ON p.pipefy_id = v.pipefy_id_projeto "
        "WHERE v.email_investidor = :e ORDER BY COALESCE(pa.nome, p.nome)"
    ), {"e": EMAIL}).fetchall()

    fmt_fila = "  {:<48} {:>10} {:>5} {:<14} {:<28}"
    print(fmt_fila.format("PROJETO", "FEE_VINC", "MOEDA", "STATUS", "FASE"))
    for v in vinc:
        pid, cien, active, inact, fee_v, nome, fee_atual, moeda, fase = v
        flags = []
        if cien: flags.append("CIENTISTA")
        if not active:
            flags.append(f"INATIVO {inact.isoformat() if inact else ''}")
        else:
            flags.append("ativo")
        nome_str = (nome or f"<sem nome pid={pid}>")[:46]
        print(fmt_fila.format(
            nome_str, str(fee_v or 0), moeda or "?", ", ".join(flags),
            (fase or "?")[:26]
        ))

with engine.connect() as c:
    # entregas_operacao + entregas_criativos em abril
    print(f"\n=== Entregas de {EMAIL} em abril/2026 ===")
    rec = c.execute(text(
        "SELECT entregas_operacao, entregas_criativos, fixo_mrr_atual, fixo_mrr_entrega, "
        "       fixo_mrr_projeto_total, fixo_churn_atual, fixo_remuneracao_minima, "
        "       fixo_remuneracao_maxima, calc_remuneracao_total, cargo "
        "FROM plataforma_geral.investidores_metricas_mensais_novo "
        "WHERE email_investidor = :e AND mes = 4 AND ano = 2026"
    ), {"e": EMAIL}).fetchone()

    if not rec:
        print("  (sem registro em abril/2026)")
    else:
        op, cri, m_atual, m_entrega, m_total, churn, rm_min, rm_max, rem_total, cargo = rec
        print(f"  cargo={cargo}")
        print(f"  fixo_mrr_atual         = {m_atual}")
        print(f"  fixo_mrr_entrega       = {m_entrega}")
        print(f"  fixo_mrr_projeto_total = {m_total}")
        print(f"  fixo_churn_atual       = {churn}")
        print(f"  rem_min/max            = {rm_min} / {rm_max}")
        print(f"  rem_total_calc         = {rem_total}")

        for nome_col, raw in (("entregas_operacao", op), ("entregas_criativos", cri)):
            if not raw: continue
            entries = raw if isinstance(raw, list) else json.loads(raw)
            print(f"\n  --- {nome_col} ({len(entries)} projeto(s)) ---")
            for proj in entries:
                pid = proj.get("projeto_id")
                cliente = proj.get("cliente")
                resp = proj.get("responsavel")
                if "entregas" in proj:
                    total_meta = sum(it.get("meta", 0) for it in proj["entregas"])
                    total_feito = sum(it.get("entregues", 0) for it in proj["entregas"])
                    progresso = (total_feito / total_meta * 100) if total_meta > 0 else 0
                    print(f"    {cliente!s:<46} pid={pid} resp={resp} progresso={progresso:.0f}%  ({total_feito}/{total_meta})")
                else:
                    cri_e = proj.get("criativos",{}).get("entregues",0)
                    cri_c = proj.get("criativos",{}).get("contratados",0)
                    lp_e  = proj.get("lp",{}).get("entregues",0)
                    lp_c  = proj.get("lp",{}).get("contratados",0)
                    vid_e = proj.get("videos",{}).get("entregues",0)
                    vid_c = proj.get("videos",{}).get("contratados",0)
                    print(f"    {cliente!s:<46} pid={pid} cri={cri_e}/{cri_c} lp={lp_e}/{lp_c} vid={vid_e}/{vid_c}")
