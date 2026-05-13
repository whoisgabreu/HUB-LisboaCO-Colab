"""Investiga por que 'Universal' (provavelmente projeto) aparece zerado em abr/2026."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

with engine.connect() as c:
    print("\n=== 1) Projetos com 'UNIVERSAL' no nome ===")
    rows = c.execute(text(
        "SELECT pipefy_id, nome, fee, moeda, fase_do_pipefy, data_de_inicio, data_fim "
        "FROM plataforma_geral.projetos_ativos "
        "WHERE nome ILIKE '%universal%'"
    )).fetchall()
    for r in rows:
        print(f"  (projetos_ativos) pid={r[0]} nome='{r[1]}' fee={r[2]} moeda={r[3]} fase={r[4]} inicio={r[5]} fim={r[6]}")
    if not rows:
        rows = c.execute(text(
            "SELECT pipefy_id, nome, fee, moeda, fase_do_pipefy, data_de_inicio, data_fim "
            "FROM plataforma_geral.projetos "
            "WHERE nome ILIKE '%universal%'"
        )).fetchall()
        for r in rows:
            print(f"  (projetos) pid={r[0]} nome='{r[1]}' fee={r[2]} moeda={r[3]} fase={r[4]} inicio={r[5]} fim={r[6]}")

    if not rows:
        print("  (nenhum projeto encontrado com 'universal' no nome)")
        sys.exit(0)

    pid = rows[0][0]
    print(f"\n=== 2) Vínculos do projeto {pid} ===")
    vinc = c.execute(text(
        "SELECT email_investidor, cientista, active, inactivated_at, fee_projeto "
        "FROM plataforma_geral.investidores_projetos "
        "WHERE pipefy_id_projeto = :p"
    ), {"p": pid}).fetchall()
    for v in vinc:
        flags = []
        if v[1]: flags.append("CIENTISTA")
        if not v[2]: flags.append(f"INATIVO desde {v[3]}")
        flag = f" [{', '.join(flags)}]" if flags else ""
        print(f"  {v[0]} fee_projeto={v[4]}{flag}")

    print(f"\n=== 3) Entregas do projeto {pid} em abr/2026 (entregas_operacao + entregas_criativos) ===")
    for v in vinc:
        email = v[0]
        rec = c.execute(text(
            "SELECT entregas_operacao, entregas_criativos, fixo_mrr_atual, fixo_mrr_entrega, fixo_mrr_projeto_total "
            "FROM plataforma_geral.investidores_metricas_mensais_novo "
            "WHERE email_investidor = :e AND mes = 4 AND ano = 2026"
        ), {"e": email}).fetchone()
        if not rec:
            print(f"  {email}: SEM REGISTRO em abr/2026")
            continue

        print(f"\n  >>> {email}")
        print(f"      mrr_atual={rec[2]} mrr_entrega={rec[3]} mrr_projeto_total={rec[4]}")
        for col_name, raw in (("entregas_operacao", rec[0]), ("entregas_criativos", rec[1])):
            if not raw:
                continue
            entries = raw if isinstance(raw, list) else json.loads(raw)
            for proj in entries:
                if str(proj.get("projeto_id")) == str(pid):
                    print(f"      {col_name}: cliente='{proj.get('cliente')}' responsavel={proj.get('responsavel')}")
                    if "entregas" in proj:
                        for it in proj.get("entregas", []):
                            print(f"        nome={it.get('nome')!r:<28} tipo={it.get('tipo')!r:<12} entregues={it.get('entregues')}/{it.get('meta')}")
                    else:
                        print(f"        criativos: {proj.get('criativos')}")
                        print(f"        videos:    {proj.get('videos')}")
                        print(f"        lp:        {proj.get('lp')}")

    print(f"\n=== 4) Snapshot operacao do projeto em abr/2026 ===")
    op = c.execute(text(
        "SELECT id, mes, ano, nome, entregas FROM plataforma_geral.operacao "
        "WHERE id_projeto = :p AND mes = 4 AND ano = 2026"
    ), {"p": str(pid)}).fetchone()
    if op:
        print(f"  id={op[0]} mes={op[1]} ano={op[2]} nome='{op[3]}'")
        e = op[4] if isinstance(op[4], dict) else json.loads(op[4]) if op[4] else {}
        for k, v in e.items():
            if isinstance(v, list):
                print(f"    {k}: {len(v)} item(s)")
            elif isinstance(v, dict):
                print(f"    {k}: {v}")
            else:
                print(f"    {k}: {v}")
    else:
        print("  (sem snapshot em abr/2026)")
