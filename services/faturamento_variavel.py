"""
Serviço de Faturamento Variável — Módulo Isolado.

Responsabilidades:
- Ler registros de faturamento variável da tabela `plataforma_geral.operacao`
  (campo JSONB `entregas["faturamento_variavel"]`)
- Calcular o valor variável por projeto/mês
- Somar ao `fixo_mrr_atual` do investidor na `MetricaMensal`
  RESPEITANDO a regra do cientista:
      resultado = (fee_fixo * 1.5) + valor_variavel
      NÃO: (fee_fixo + valor_variavel) * 1.5

Restrições:
- NÃO modifica serviços existentes.
- NÃO altera schema do banco.
- NÃO altera cálculos existentes de remuneração.
"""

import json
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text
from database import Session, engine
from models import MetricaMensal, InvestidorProjeto, ProjetoAtivo


def _get_faturamentos_variavel_projeto(conn, pipefy_id, mes, ano):
    """
    Retorna a lista de registros de faturamento variável para um projeto/mês/ano.
    Lê de plataforma_geral.operacao.entregas["faturamento_variavel"].
    """
    row = conn.execute(text(
        "SELECT entregas FROM plataforma_geral.operacao "
        "WHERE id_projeto = :id AND mes = :mes AND ano = :ano LIMIT 1"
    ), {"id": str(pipefy_id), "mes": int(mes), "ano": int(ano)}).first()

    if not row or row.entregas is None:
        return []

    entregas = row.entregas if isinstance(row.entregas, dict) else json.loads(row.entregas)
    return entregas.get("faturamento_variavel", [])


def _get_valor_variavel_projeto(pipefy_id, mes, ano):
    """
    Retorna o valor_variavel total de um projeto para um mês/ano específico.
    Se houver múltiplos registros no mês, soma todos.
    """
    try:
        with engine.connect() as conn:
            registros = _get_faturamentos_variavel_projeto(conn, pipefy_id, mes, ano)
            total = Decimal("0")
            for reg in registros:
                if reg.get("mes") == mes and reg.get("ano") == ano:
                    total += Decimal(str(reg.get("valor_variavel", 0)))
            return total
    except Exception as e:
        print(f"[faturamento_variavel] Erro ao obter valor_variavel {pipefy_id}: {e}")
        return Decimal("0")


def aplicar_faturamento_variavel(mes, ano):
    """
    Pós-processamento do cálculo de remuneração:
    Para cada investidor ativo, soma o valor variável dos projetos com contrato variável
    ao `fixo_mrr_atual` na MetricaMensal.

    Regra do Cientista:
        O multiplicador 1.5x já está aplicado no fee_fixo pelo services/remuneracao.py.
        O valor_variavel é somado DEPOIS, sem participar do multiplicador.
        Portanto: resultado_final = mrr_base_com_cientista + valor_variavel

    Esta função é idempotente — pode ser chamada múltiplas vezes sem efeito colateral.
    """
    print(f"[faturamento_variavel] Aplicando valores variáveis para {mes}/{ano}")

    try:
        with Session() as db:
            # 1. Buscar todos os projetos ativos com contrato_variavel = True
            #    A flag está em ProjetoAtivo.extra["contrato_variavel"]
            projetos_ativos = db.query(ProjetoAtivo).all()
            projetos_variaveis = {
                p.pipefy_id: p
                for p in projetos_ativos
                if (p.extra or {}).get("contrato_variavel") is True
            }

            if not projetos_variaveis:
                print(f"[faturamento_variavel] Nenhum projeto com contrato variável encontrado.")
                return

            print(f"[faturamento_variavel] Projetos variáveis: {list(projetos_variaveis.keys())}")

            # 2. Para cada projeto variável, buscar o valor do mês
            valores_por_projeto = {}
            with engine.connect() as conn:
                for pid, projeto in projetos_variaveis.items():
                    registros = _get_faturamentos_variavel_projeto(conn, pid, mes, ano)
                    total_variavel = Decimal("0")
                    for reg in registros:
                        if reg.get("mes") == mes and reg.get("ano") == ano:
                            total_variavel += Decimal(str(reg.get("valor_variavel", 0)))
                    if total_variavel > 0:
                        valores_por_projeto[pid] = total_variavel
                        print(f"[faturamento_variavel] Projeto {pid}: R$ {total_variavel}")

            if not valores_por_projeto:
                print(f"[faturamento_variavel] Nenhum valor variável registrado para {mes}/{ano}.")
                return

            # 3. Para cada investidor vinculado a projetos variáveis, atualizar MetricaMensal
            vinculos = db.query(InvestidorProjeto).filter(
                InvestidorProjeto.pipefy_id_projeto.in_(list(valores_por_projeto.keys())),
                InvestidorProjeto.active == True
            ).all()

            # Agrupa por investidor: email → soma de valores variáveis dos projetos vinculados
            soma_por_investidor = {}
            for v in vinculos:
                pid = v.pipefy_id_projeto
                val = valores_por_projeto.get(pid, Decimal("0"))
                if val == Decimal("0"):
                    continue

                email = v.email_investidor
                if email not in soma_por_investidor:
                    soma_por_investidor[email] = Decimal("0")
                soma_por_investidor[email] += val

            print(f"[faturamento_variavel] Investidores impactados: {list(soma_por_investidor.keys())}")

            # 4. Atualizar fixo_mrr_atual e fixo_mrr_entrega somando o valor variável
            #    O valor base já contém o multiplicador 1.5x do cientista (feito pelo remuneracao.py)
            #    Apenas somamos o valor variável por cima — respeitando a regra:
            #        resultado = fee_cientista_base + valor_variavel
            for email, valor_variavel_total in soma_por_investidor.items():
                metrica = db.query(MetricaMensal).filter_by(
                    email_investidor=email,
                    mes=mes,
                    ano=ano
                ).first()

                if not metrica:
                    print(f"[faturamento_variavel] Sem MetricaMensal para {email} {mes}/{ano} — pulando.")
                    continue

                mrr_base = Decimal(str(metrica.fixo_mrr_atual or 0))
                novo_mrr = mrr_base + valor_variavel_total

                metrica.fixo_mrr_atual = novo_mrr
                metrica.fixo_mrr_entrega = novo_mrr

                print(
                    f"[faturamento_variavel] {email}: "
                    f"mrr_base={float(mrr_base):.2f} + variavel={float(valor_variavel_total):.2f} "
                    f"= {float(novo_mrr):.2f}"
                )

                db.flush()

            db.commit()
            print(f"[faturamento_variavel] Concluído para {mes}/{ano}.")

    except Exception as e:
        import traceback
        print(f"[faturamento_variavel] ERRO: {e}")
        traceback.print_exc()


def get_registros_por_projeto(pipefy_id, mes=None, ano=None):
    """
    Retorna todos os registros de faturamento variável de um projeto.
    Se mes/ano forem fornecidos, filtra pelo mês/ano.
    Usado pelas APIs REST.
    """
    try:
        with engine.connect() as conn:
            if mes is not None and ano is not None:
                registros = _get_faturamentos_variavel_projeto(conn, pipefy_id, mes, ano)
                return [r for r in registros if r.get("mes") == mes and r.get("ano") == ano]
            else:
                # Retorna todos os meses disponíveis na tabela operacao para este projeto
                rows = conn.execute(text(
                    "SELECT mes, ano, entregas FROM plataforma_geral.operacao "
                    "WHERE id_projeto = :id ORDER BY ano DESC, mes DESC"
                ), {"id": str(pipefy_id)}).fetchall()

                todos = []
                for row in rows:
                    if not row.entregas:
                        continue
                    entregas = row.entregas if isinstance(row.entregas, dict) else json.loads(row.entregas)
                    fat_var = entregas.get("faturamento_variavel", [])
                    for reg in fat_var:
                        if reg.get("mes") == row.mes and reg.get("ano") == row.ano:
                            todos.append(reg)
                return todos
    except Exception as e:
        print(f"[faturamento_variavel] Erro em get_registros_por_projeto: {e}")
        return []


def salvar_registro(pipefy_id, mes, ano, faturamento_cliente, percentual, usuario_email):
    """
    Cria ou atualiza o registro de faturamento variável de um projeto/mês/ano.
    O valor_variavel é calculado automaticamente.
    Retorna (sucesso: bool, mensagem: str).
    """
    try:
        valor_variavel = float(faturamento_cliente) * (float(percentual) / 100)

        novo_registro = {
            "mes": int(mes),
            "ano": int(ano),
            "faturamento_cliente": float(faturamento_cliente),
            "percentual": float(percentual),
            "valor_variavel": round(valor_variavel, 2),
            "criado_em": datetime.now().isoformat(),
            "criado_por": usuario_email
        }

        with engine.begin() as conn:
            row = conn.execute(text(
                "SELECT id, entregas FROM plataforma_geral.operacao "
                "WHERE id_projeto = :id AND mes = :mes AND ano = :ano LIMIT 1"
            ), {"id": str(pipefy_id), "mes": int(mes), "ano": int(ano)}).mappings().first()

            if row:
                current_raw = row["entregas"]
                current = current_raw if isinstance(current_raw, dict) else (
                    json.loads(current_raw) if current_raw else {}
                )
                # Substitui o registro do mês (apenas um por mês/ano)
                current["faturamento_variavel"] = [
                    r for r in current.get("faturamento_variavel", [])
                    if not (r.get("mes") == int(mes) and r.get("ano") == int(ano))
                ]
                current["faturamento_variavel"].append(novo_registro)

                conn.execute(text(
                    "UPDATE plataforma_geral.operacao "
                    "SET entregas = CAST(:ent AS jsonb) "
                    "WHERE id_projeto = :id AND mes = :mes AND ano = :ano"
                ), {
                    "ent": json.dumps(current, ensure_ascii=False),
                    "id": str(pipefy_id),
                    "mes": int(mes),
                    "ano": int(ano)
                })
            else:
                # Cria novo snapshot mínimo com o registro variável
                from database import engine as _engine
                # Busca nome do projeto
                with Session() as ndb:
                    from models import ProjetoAtivo, ProjetoOnetime
                    proj = (
                        ndb.query(ProjetoAtivo).filter_by(pipefy_id=pipefy_id).first()
                        or ndb.query(ProjetoOnetime).filter_by(pipefy_id=pipefy_id).first()
                    )
                    nome_proj = proj.nome if proj else ""

                novo_snap = {"faturamento_variavel": [novo_registro]}
                conn.execute(text(
                    "INSERT INTO plataforma_geral.operacao (id_projeto, mes, ano, nome, entregas) "
                    "VALUES (:id, :mes, :ano, :nome, CAST(:ent AS jsonb))"
                ), {
                    "id": str(pipefy_id),
                    "mes": int(mes),
                    "ano": int(ano),
                    "nome": nome_proj,
                    "ent": json.dumps(novo_snap, ensure_ascii=False)
                })

        return True, f"Registro salvo: R$ {valor_variavel:,.2f}"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, str(e)


def deletar_registro(pipefy_id, mes, ano):
    """
    Remove o registro de faturamento variável de um projeto/mês/ano.
    Retorna (sucesso: bool, mensagem: str).
    """
    try:
        with engine.begin() as conn:
            row = conn.execute(text(
                "SELECT id, entregas FROM plataforma_geral.operacao "
                "WHERE id_projeto = :id AND mes = :mes AND ano = :ano LIMIT 1"
            ), {"id": str(pipefy_id), "mes": int(mes), "ano": int(ano)}).mappings().first()

            if not row:
                return False, "Registro não encontrado."

            current_raw = row["entregas"]
            current = current_raw if isinstance(current_raw, dict) else (
                json.loads(current_raw) if current_raw else {}
            )
            fat_var = current.get("faturamento_variavel", [])
            nova_lista = [
                r for r in fat_var
                if not (r.get("mes") == int(mes) and r.get("ano") == int(ano))
            ]
            current["faturamento_variavel"] = nova_lista

            conn.execute(text(
                "UPDATE plataforma_geral.operacao "
                "SET entregas = CAST(:ent AS jsonb) "
                "WHERE id_projeto = :id AND mes = :mes AND ano = :ano"
            ), {
                "ent": json.dumps(current, ensure_ascii=False),
                "id": str(pipefy_id),
                "mes": int(mes),
                "ano": int(ano)
            })

        return True, "Registro removido com sucesso."

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, str(e)
