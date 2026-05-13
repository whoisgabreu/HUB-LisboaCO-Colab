"""Investigação completa: Universal Countertop / Universal Countertop 2 em abr/2026."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

PIDS = {1177672586: "Universal Countertop 2", 1071290432: "Universal Countertop"}

with engine.connect() as c:
    for pid, nome in PIDS.items():
        print(f"\n{'='*70}\n   {nome} (pid={pid})\n{'='*70}")

        # 1) Vínculos
        vinc = c.execute(text(
            "SELECT email_investidor, cientista, active, inactivated_at, fee_projeto "
            "FROM plataforma_geral.investidores_projetos WHERE pipefy_id_projeto = :p"
        ), {"p": pid}).fetchall()
        print(f"\n  >> Vínculos ({len(vinc)}):")
        for v in vinc:
            flags = []
            if v[1]: flags.append("CIENTISTA")
            if not v[2]: flags.append(f"INATIVO desde {v[3]}")
            print(f"     {v[0]} fee={v[4]} {flags}")

        # 2) entregas_operacao + entregas_criativos em abril/2026 que mencionem este pid
        print(f"\n  >> Em entregas_operacao/criativos (abr/2026):")
        rows = c.execute(text(
            "SELECT email_investidor, entregas_operacao, entregas_criativos, "
            "fixo_mrr_atual, fixo_mrr_entrega "
            "FROM plataforma_geral.investidores_metricas_mensais_novo "
            "WHERE mes = 4 AND ano = 2026"
        )).fetchall()
        achou = False
        for email, op, cri, m_atual, m_entrega in rows:
            for col_name, raw in (("op", op), ("cri", cri)):
                if not raw: continue
                entries = raw if isinstance(raw, list) else json.loads(raw)
                for proj in entries:
                    if str(proj.get("projeto_id")) == str(pid):
                        achou = True
                        print(f"     {email} ({col_name}) responsavel={proj.get('responsavel')} mrr_atual={m_atual}")
                        if "entregas" in proj:
                            for it in proj["entregas"]:
                                print(f"        nome={it.get('nome')!r:<28} entregues={it.get('entregues')}/{it.get('meta')}")
                        else:
                            for k in ("criativos","videos","lp"):
                                if k in proj:
                                    print(f"        {k}: {proj[k]}")
        if not achou:
            print("     (nenhum investidor tem esse projeto no entregas em abr/2026)")

        # 3) Snapshot na tabela operacao
        print(f"\n  >> Snapshot plataforma_geral.operacao (abr/2026):")
        op = c.execute(text(
            "SELECT id, mes, ano, nome, entregas FROM plataforma_geral.operacao "
            "WHERE id_projeto = :p AND mes = 4 AND ano = 2026"
        ), {"p": str(pid)}).fetchone()
        if op:
            e = op[4] if isinstance(op[4], dict) else json.loads(op[4]) if op[4] else {}
            print(f"     id={op[0]} nome='{op[3]}'")
            for k, v in e.items():
                if isinstance(v, list):
                    print(f"        {k}: {len(v)} item(s)")
                elif isinstance(v, dict):
                    desc = ", ".join(f"{kk}={vv}" for kk, vv in v.items()) if v else "vazio"
                    print(f"        {k}: {{{desc}}}")
                else:
                    print(f"        {k}: {v}")
        else:
            print("     (sem snapshot em abr/2026)")

        # 4) Tabelas operacao_planos_midia / otimizacoes / checkins / tarefas em abril
        print(f"\n  >> Tabelas auxiliares /operacao em abr/2026:")
        for tname, key_col in (
            ("operacao_planos_midia", "projeto_pipefy_id"),
            ("operacao_otimizacoes", "projeto_pipefy_id"),
            ("operacao_checkins", "projeto_pipefy_id"),
            ("operacao_tarefas", "projeto_pipefy_id"),
        ):
            try:
                cnt = c.execute(text(
                    f"SELECT COUNT(*) FROM plataforma_geral.{tname} WHERE {key_col} = :p"
                ), {"p": pid}).scalar()
                print(f"     {tname}: {cnt} registro(s)")
            except Exception as e:
                print(f"     {tname}: erro -> {e}")
