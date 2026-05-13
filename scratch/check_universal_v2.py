"""Diagnóstico Universal — versão simplificada."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from database import engine

PIDS = {1177672586: "Universal Countertop 2", 1071290432: "Universal Countertop"}

for pid, nome in PIDS.items():
    print(f"\n{'='*70}\n   {nome} (pid={pid})\n{'='*70}")

    # Conexão nova por bloco para evitar transaction abort
    with engine.connect() as c:
        # 1) Em projetos_ativos? (cargo de "ativo" oficial)
        ativo = c.execute(text(
            "SELECT pipefy_id, nome, fee, fase_do_pipefy, data_de_inicio "
            "FROM plataforma_geral.projetos_ativos WHERE pipefy_id = :p"
        ), {"p": pid}).fetchone()
        print(f"\n  [projetos_ativos] {'ENCONTRADO -> ' + str(dict(ativo._mapping)) if ativo else 'NÃO está em projetos_ativos'}")

        # 2) Em projetos
        proj = c.execute(text(
            "SELECT pipefy_id, nome, fee, fase_do_pipefy, data_de_inicio "
            "FROM plataforma_geral.projetos WHERE pipefy_id = :p"
        ), {"p": pid}).fetchone()
        print(f"  [projetos] {'ENCONTRADO -> ' + str(dict(proj._mapping)) if proj else 'não está'}")

    with engine.connect() as c:
        # 3) Vínculos
        vinc = c.execute(text(
            "SELECT email_investidor, cientista, active, inactivated_at, fee_projeto "
            "FROM plataforma_geral.investidores_projetos WHERE pipefy_id_projeto = :p"
        ), {"p": pid}).fetchall()
        print(f"\n  [vínculos] total={len(vinc)}")
        for v in vinc:
            tags = []
            if v[1]: tags.append("CIENTISTA")
            if not v[2]: tags.append(f"INATIVO {v[3]}")
            print(f"     {v[0]} fee={v[4]} {tags}")

    with engine.connect() as c:
        # 4) Em entregas_operacao/criativos de qualquer investidor em abr/2026
        rows = c.execute(text(
            "SELECT email_investidor, entregas_operacao, entregas_criativos, "
            "fixo_mrr_atual, fixo_mrr_entrega "
            "FROM plataforma_geral.investidores_metricas_mensais_novo "
            "WHERE mes = 4 AND ano = 2026"
        )).fetchall()
        print(f"\n  [entregas em abr/2026]")
        achou = False
        for email, op, cri, m_atual, m_entrega in rows:
            for col, raw in (("op", op), ("cri", cri)):
                if not raw: continue
                entries = raw if isinstance(raw, list) else json.loads(raw)
                for proj in entries:
                    if str(proj.get("projeto_id")) == str(pid):
                        achou = True
                        print(f"     {email} ({col}) responsavel={proj.get('responsavel')} mrr_entrega_total={m_entrega}")
                        if "entregas" in proj:
                            for it in proj["entregas"]:
                                print(f"        nome={it.get('nome')!r:<28} entregues={it.get('entregues')}/{it.get('meta')}")
                        else:
                            for k in ("criativos","videos","lp"):
                                if k in proj:
                                    print(f"        {k}: {proj[k]}")
        if not achou:
            print("     (nenhum investidor tem este projeto no entregas em abr/2026)")

    with engine.connect() as c:
        # 5) Snapshot operacao
        op = c.execute(text(
            "SELECT id, mes, ano, nome, entregas FROM plataforma_geral.operacao "
            "WHERE id_projeto = :p AND mes = 4 AND ano = 2026"
        ), {"p": str(pid)}).fetchone()
        print(f"\n  [tabela operacao em abr/2026] {'EXISTE -> id=' + str(op[0]) if op else 'sem snapshot'}")
        if op and op[4]:
            e = op[4] if isinstance(op[4], dict) else json.loads(op[4])
            for k, v in e.items():
                if isinstance(v, list):
                    print(f"        {k}: {len(v)} item(s)")
                elif isinstance(v, dict):
                    print(f"        {k}: {v}")
                else:
                    print(f"        {k}: {v}")
