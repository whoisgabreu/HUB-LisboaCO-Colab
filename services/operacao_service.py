import copy
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from models import (
    InvestidorProjeto, ProjetoAtivo, ProjetoOnetime,
    MetricaMensal, Investidor, OperacaoTarefa,
)

class OperacaoService:
    @staticmethod
    def get_projetos_operacao(db: Session, email: str, squad: str, posicao: str = None) -> list:
        """
        Retorna todos os projetos vinculados e ativos ao usuário para a tela de operação.
        Considera Projetos Ativos, Onetime e Inativos.
        """
        todas_tabelas = [ProjetoAtivo, ProjetoOnetime]
        meus_projetos_dict = {}

        if squad == "Gerência" or posicao in ["Gerência", "Sócio"]:
            # Para gerência, buscar de todas as tabelas
            for model in todas_tabelas:
                projetos = db.query(model).all()
                for p in projetos:
                    if p.pipefy_id not in meus_projetos_dict:
                        meus_projetos_dict[p.pipefy_id] = p
        else:
            # Busca vínculos ativos do investidor
            vinculos = db.query(InvestidorProjeto).filter(
                InvestidorProjeto.email_investidor == email,
                InvestidorProjeto.active == True
            ).all()
            
            # Extrai os IDs dos projetos vinculados
            ids_vinculados = [v.pipefy_id_projeto for v in vinculos]
            
            if ids_vinculados:
                for model in todas_tabelas:
                    projetos = db.query(model).filter(model.pipefy_id.in_(ids_vinculados)).all()
                    for p in projetos:
                        if p.pipefy_id not in meus_projetos_dict:
                            meus_projetos_dict[p.pipefy_id] = p

        # Prepara a lista a ser retornada
        # Mapeamos os vínculos para saber quem é cientista
        vinculos_map = {v.pipefy_id_projeto: v.cientista for v in vinculos} if 'vinculos' in locals() else {}

        meus_projetos = []
        for p in meus_projetos_dict.values():
            meus_projetos.append({
                "id": p.pipefy_id,
                "pipefy_id": p.pipefy_id,
                "nome": p.nome,
                "documento": getattr(p, "documento", ""),
                "fee": getattr(p, "fee", 0),
                "moeda": getattr(p, "moeda", ""),
                "squad_atribuida": getattr(p, "squad_atribuida", ""),
                "produto_contratado": getattr(p, "produto_contratado", ""),
                "data_de_inicio": p.data_de_inicio.isoformat() if getattr(p, "data_de_inicio", None) else None,
                "cohort": getattr(p, "cohort", ""),
                "meta_account_id": getattr(p, "meta_account_id", ""),
                "google_account_id": getattr(p, "google_account_id", ""),
                "fase_do_pipefy": getattr(p, "fase_do_pipefy", ""),
                "step": getattr(p, "step", ""),
                "informacoes_gerais": getattr(p, "informacoes_gerais", ""),
                "orcamento_midia_meta": getattr(p, "orcamento_midia_meta", 0),
                "orcamento_midia_google": getattr(p, "orcamento_midia_google", 0),
                "data_fim": p.data_fim.isoformat() if getattr(p, "data_fim", None) else None,
                "ekyte_workspace": getattr(p, "ekyte_workspace", ""),
                "cientista": vinculos_map.get(p.pipefy_id, False)
            })

        return meus_projetos


class OperacaoSnapshotService:
    """
    Gerencia o snapshot consolidado de entregas por projeto+mês na tabela
    plataforma_geral.operacao usando SQL puro para máxima compatibilidade.
    """

    SCHEMA = "plataforma_geral"
    TABLE  = "operacao"

    _EMPTY = {
        "plano_midia":      {"budget_total": 0, "planos": []},
        "otimizacoes":      [],
        "forecasting":      {"link": ""},
        "kpis":             {"link": ""},
        "checkin_semanal":  [],
        "relatorio_account":{"link": ""},
        "relatorio_gt":     {"link": ""},
        "metas":            {},
    }

    # ── helpers SQL puros ───────────────────────────────────────────────────

    @staticmethod
    def _get_row(db, id_projeto, mes, ano):
        from sqlalchemy import text
        row = db.execute(text(
            f"SELECT id, nome, entregas FROM {OperacaoSnapshotService.SCHEMA}.{OperacaoSnapshotService.TABLE} "
            "WHERE id_projeto = :id_projeto AND mes = :mes AND ano = :ano LIMIT 1"
        ), {"id_projeto": str(id_projeto), "mes": int(mes), "ano": int(ano)}).first()
        return row

    @staticmethod
    def _insert_row(db, id_projeto, mes, ano, nome, entregas_json):
        from sqlalchemy import text
        import json as _json
        db.execute(text(
            f"INSERT INTO {OperacaoSnapshotService.SCHEMA}.{OperacaoSnapshotService.TABLE} "
            "(mes, ano, nome, id_projeto, entregas) "
            "VALUES (:mes, :ano, :nome, :id_projeto, CAST(:entregas AS jsonb))"
        ), {
            "mes":        int(mes),
            "ano":        int(ano),
            "nome":       nome or "",
            "id_projeto": str(id_projeto),
            "entregas":   _json.dumps(entregas_json, ensure_ascii=False),
        })

    @staticmethod
    def _update_row(db, row_id, entregas_json, nome=None):
        from sqlalchemy import text
        import json as _json
        if nome:
            db.execute(text(
                f"UPDATE {OperacaoSnapshotService.SCHEMA}.{OperacaoSnapshotService.TABLE} "
                "SET entregas = CAST(:entregas AS jsonb), nome = :nome WHERE id = :id"
            ), {"entregas": _json.dumps(entregas_json, ensure_ascii=False), "nome": nome, "id": row_id})
        else:
            db.execute(text(
                f"UPDATE {OperacaoSnapshotService.SCHEMA}.{OperacaoSnapshotService.TABLE} "
                "SET entregas = CAST(:entregas AS jsonb) WHERE id = :id"
            ), {"entregas": _json.dumps(entregas_json, ensure_ascii=False), "id": row_id})

    # ── interface pública ───────────────────────────────────────────────────

    @staticmethod
    def update_section(db, id_projeto, mes, ano, section_key, new_data,
                       append=False, nome=None):
        """Upsert: cria o registro se não existir, depois atualiza a seção."""
        row = OperacaoSnapshotService._get_row(db, id_projeto, mes, ano)

        if row is None:
            # Criar novo registro com a seção já preenchida
            entregas = copy.deepcopy(OperacaoSnapshotService._EMPTY)
            if append:
                entregas[section_key] = [new_data]
            else:
                entregas[section_key] = new_data
            OperacaoSnapshotService._insert_row(db, id_projeto, mes, ano, nome, entregas)
        else:
            # Atualizar seção no registro existente
            import json as _json
            entregas = row.entregas if isinstance(row.entregas, dict) else (
                _json.loads(row.entregas) if row.entregas else copy.deepcopy(OperacaoSnapshotService._EMPTY)
            )
            if append:
                lst = list(entregas.get(section_key) or [])
                lst.append(new_data)
                entregas[section_key] = lst
            else:
                entregas[section_key] = new_data
            nome_final = nome or (row.nome if row.nome else None)
            OperacaoSnapshotService._update_row(db, row.id, entregas, nome=nome_final)

    @staticmethod
    def get_snapshot(db, id_projeto, mes, ano):
        """Retorna o dict de entregas para o projeto+mês, ou None se não existir."""
        import json as _json
        row = OperacaoSnapshotService._get_row(db, id_projeto, mes, ano)
        if not row:
            return None
        if isinstance(row.entregas, dict):
            return row.entregas
        try:
            return _json.loads(row.entregas) if row.entregas else None
        except Exception:
            return None

    @staticmethod
    def sync_to_metrica(db, email, id_projeto, mes, ano):
        """
        Lê operacao.entregas e atualiza MetricaMensal.entregas_operacao.
        Retorna o record MetricaMensal modificado (sem commit).
        """
        now = datetime.now()
        if ano < now.year or (ano == now.year and mes < now.month):
            return None

        investidor = db.query(Investidor).filter(Investidor.email.ilike(email)).first()
        if not investidor:
            return None

        funcao = investidor.funcao or ""
        is_gt      = funcao in ("Gestor de Tráfego", "Cientista", "Desenvolvedor")
        is_account = funcao in ("Account", "Cientista")

        snap = OperacaoSnapshotService.get_snapshot(db, id_projeto, mes, ano)
        if snap is None:
            return None

        metrica = db.query(MetricaMensal).filter_by(
            email_investidor=email, mes=mes, ano=ano
        ).first()
        if not metrica:
            return None

        lista_op   = list(metrica.entregas_operacao or [])
        proj_entry = next(
            (e for e in lista_op if str(e.get("projeto_id")) == str(id_projeto)), None
        )
        if proj_entry is None:
            return None

        plano_planos        = (snap.get("plano_midia") or {}).get("planos") or []
        otims               = snap.get("otimizacoes") or []
        checkins            = snap.get("checkin_semanal") or []
        kpis_link           = (snap.get("kpis") or {}).get("link") or ""
        forecasting_link    = (snap.get("forecasting") or {}).get("link") or ""
        relatorio_gt_link   = (snap.get("relatorio_gt") or {}).get("link") or ""
        relatorio_acc_link  = (snap.get("relatorio_account") or {}).get("link") or ""
        relatorio_mensal_link = (snap.get("relatorio_mensal") or {}).get("link") or ""

        entregues_map, links_map = {}, {}

        if is_gt:
            entregues_map["plano_de_midia"]         = 1 if plano_planos else 0
            entregues_map["documento_de_otimizacao"] = min(len(otims), 4)
            entregues_map["kpis"]                    = 1 if kpis_link else 0
            if kpis_link:
                links_map["link_kpi"] = kpis_link

        if is_account:
            entregues_map["csat_checkin"] = min(len(checkins), 4)
            entregues_map["forecasting"]  = 1 if forecasting_link else 0
            if forecasting_link:
                links_map["link_forecast"] = forecasting_link

            # Planner Monday — protegido com SAVEPOINT pois a tabela pode não existir
            count_semanal = 0
            try:
                nested = db.begin_nested()
                tarefas = db.query(OperacaoTarefa).filter_by(
                    projeto_pipefy_id=id_projeto, tipo="semanal", ano=ano
                ).all()
                for t in tarefas:
                    try:
                        if t.referencia and "-W" in t.referencia:
                            y, w = map(int, t.referencia.split("-W"))
                            d = datetime.fromisocalendar(y, w, 1)
                            if d.month == mes:
                                count_semanal += 1
                    except Exception:
                        pass
                nested.commit()
            except Exception:
                # Tabela operacao_tarefas pode não existir — rollback do savepoint
                try:
                    nested.rollback()
                except Exception:
                    pass
                count_semanal = 0
            entregues_map["planner_monday"] = min(count_semanal, 4)

        if is_gt and not is_account:
            rel = relatorio_gt_link or relatorio_mensal_link
            entregues_map["relatorio_mensal"] = 1 if rel else 0
            if rel:
                links_map["link_relatorio"] = rel
        elif is_account and not is_gt:
            rel = relatorio_acc_link or relatorio_mensal_link
            entregues_map["relatorio_mensal"] = 1 if rel else 0
            if rel:
                links_map["link_relatorio"] = rel
        elif is_gt and is_account:
            rel = relatorio_gt_link or relatorio_acc_link or relatorio_mensal_link
            entregues_map["relatorio_mensal"] = 1 if rel else 0
            if rel:
                links_map["link_relatorio"] = rel

        changed = False
        for entrega in proj_entry.get("entregas", []):
            n = entrega.get("nome")
            if n in entregues_map and entrega.get("entregues") != entregues_map[n]:
                entrega["entregues"] = entregues_map[n]
                changed = True
        for k, v in links_map.items():
            if proj_entry.get(k) != v:
                proj_entry[k] = v
                changed = True

        if changed:
            flag_modified(metrica, "entregas_operacao")

        return metrica
