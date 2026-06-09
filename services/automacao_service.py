import json
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
import requests

from models import Automacao, AutomacaoLog, Projeto, KanbanConfig, KanbanHistorico

logger = logging.getLogger(__name__)

TRIGGER_TYPES = [
    {"id": "card_entered_phase", "name": "Card entrou em uma fase", "group": "kanban"},
    {"id": "card_left_phase", "name": "Card saiu de uma fase", "group": "kanban"},
    {"id": "card_moved", "name": "Card foi movido entre fases", "group": "kanban"},
    {"id": "card_created", "name": "Card foi criado", "group": "kanban"},
    {"id": "card_archived", "name": "Card foi arquivado", "group": "kanban"},
    {"id": "project_days_before", "name": "Faltam X dias para a data do projeto", "group": "project"},
    {"id": "project_date_today", "name": "Data do projeto é hoje", "group": "project"},
    {"id": "project_days_after", "name": "Passaram X dias da data do projeto", "group": "project"},
]

VARIABLES = [
    {"key": "{{card_id}}", "description": "ID do card"},
    {"key": "{{card_title}}", "description": "Título/nome do card"},
    {"key": "{{phase_id}}", "description": "ID da fase"},
    {"key": "{{phase_name}}", "description": "Nome da fase"},
    {"key": "{{project_id}}", "description": "ID do projeto"},
    {"key": "{{project_name}}", "description": "Nome do projeto"},
    {"key": "{{project_date}}", "description": "Data do projeto"},
    {"key": "{{current_date}}", "description": "Data atual"},
]


class AutomacaoService:
    def __init__(self, db: Session):
        self.db = db

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def list_automacoes(self) -> List[Dict[str, Any]]:
        result = self.db.execute(select(Automacao).order_by(desc(Automacao.created_at)))
        return [self._to_dict(a) for a in result.scalars().all()]

    def get_automacao(self, automacao_id: int) -> Optional[Dict[str, Any]]:
        a = self.db.execute(select(Automacao).where(Automacao.id == automacao_id)).scalar_one_or_none()
        return self._to_dict(a) if a else None

    def create_automacao(self, data: Dict[str, Any]) -> Automacao:
        a = Automacao(
            nome=data["nome"],
            descricao=data.get("descricao", ""),
            ativa=data.get("ativa", True),
            trigger_type=data["trigger_type"],
            trigger_config=data.get("trigger_config", {}),
            action_type="webhook",
            action_config=data.get("action_config", {}),
        )
        self.db.add(a)
        self.db.commit()
        self.db.refresh(a)
        return a

    def update_automacao(self, automacao_id: int, data: Dict[str, Any]) -> Automacao:
        a = self.db.execute(select(Automacao).where(Automacao.id == automacao_id)).scalar_one_or_none()
        if not a:
            raise ValueError("Automação não encontrada.")
        if "nome" in data:
            a.nome = data["nome"]
        if "descricao" in data:
            a.descricao = data["descricao"]
        if "ativa" in data:
            a.ativa = data["ativa"]
        if "trigger_type" in data:
            a.trigger_type = data["trigger_type"]
        if "trigger_config" in data:
            a.trigger_config = data["trigger_config"]
        if "action_config" in data:
            a.action_config = data["action_config"]
        a.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(a)
        return a

    def delete_automacao(self, automacao_id: int):
        a = self.db.execute(select(Automacao).where(Automacao.id == automacao_id)).scalar_one_or_none()
        if not a:
            raise ValueError("Automação não encontrada.")
        self.db.delete(a)
        self.db.commit()

    def toggle_automacao(self, automacao_id: int) -> bool:
        a = self.db.execute(select(Automacao).where(Automacao.id == automacao_id)).scalar_one_or_none()
        if not a:
            raise ValueError("Automação não encontrada.")
        a.ativa = not a.ativa
        a.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(a)
        return a.ativa

    # ── Logs ──────────────────────────────────────────────────────────────────

    def list_logs(self, limit: int = 100, automacao_id: Optional[int] = None) -> List[Dict[str, Any]]:
        q = select(AutomacaoLog).order_by(desc(AutomacaoLog.executed_at))
        if automacao_id:
            q = q.where(AutomacaoLog.automacao_id == automacao_id)
        q = q.limit(limit)
        result = self.db.execute(q)
        return [self._log_to_dict(l) for l in result.scalars().all()]

    def _log_to_dict(self, log: AutomacaoLog) -> Dict[str, Any]:
        return {
            "id": log.id,
            "automacao_id": log.automacao_id,
            "automacao_nome": log.automacao_nome,
            "event_type": log.event_type,
            "card_id": log.card_id,
            "project_id": log.project_id,
            "url_chamada": log.url_chamada,
            "http_status": log.http_status,
            "status": log.status,
            "error_message": log.error_message,
            "executed_at": log.executed_at.isoformat() if log.executed_at else None,
        }

    # ── Trigger matching ──────────────────────────────────────────────────────

    def _get_active_automations_for_trigger(self, trigger_type: str) -> List[Automacao]:
        result = self.db.execute(
            select(Automacao).where(
                Automacao.ativa == True,
                Automacao.trigger_type == trigger_type
            )
        )
        return list(result.scalars().all())

    def _substitute_variables(self, template: str, context: Dict[str, Any]) -> str:
        if not template:
            return template
        result = template
        for var_info in VARIABLES:
            key = var_info["key"]
            var_name = key.strip("{}")
            value = context.get(var_name, key)
            if value is None:
                value = ""
            result = result.replace(key, str(value))
        return result

    def _execute_webhook(self, automacao: Automacao, context: Dict[str, Any]) -> AutomacaoLog:
        action_config = automacao.action_config or {}
        url = action_config.get("url", "")
        method = action_config.get("method", "POST").upper()
        content_type = action_config.get("content_type", "json")
        headers = dict(action_config.get("headers", {}))
        token = action_config.get("token", "")
        payload_template = action_config.get("payload", "")

        if token:
            headers["Authorization"] = f"Bearer {token}"

        url = self._substitute_variables(url, context)

        if content_type == "json":
            if payload_template:
                try:
                    substituted = self._substitute_variables(payload_template, context)
                    payload = json.loads(substituted)
                except json.JSONDecodeError:
                    payload = self._substitute_variables(payload_template, context)
            else:
                payload = {k.strip("{}"): v for k, v in context.items()}
            headers.setdefault("Content-Type", "application/json")
            data = json.dumps(payload) if isinstance(payload, dict) else payload
        else:
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
            data = self._substitute_variables(payload_template or "", context)

        log_entry = AutomacaoLog(
            automacao_id=automacao.id,
            automacao_nome=automacao.nome,
            event_type=context.get("event_type", ""),
            card_id=context.get("card_id"),
            project_id=context.get("project_id"),
            url_chamada=url,
        )

        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=30)
            elif method == "PUT":
                resp = requests.put(url, headers=headers, data=data, timeout=30)
            elif method == "PATCH":
                resp = requests.patch(url, headers=headers, data=data, timeout=30)
            else:
                resp = requests.post(url, headers=headers, data=data, timeout=30)

            log_entry.http_status = resp.status_code
            if 200 <= resp.status_code < 300:
                log_entry.status = "success"
            else:
                log_entry.status = "failure"
                log_entry.error_message = f"HTTP {resp.status_code}: {resp.text[:500]}"
        except Exception as e:
            log_entry.http_status = 0
            log_entry.status = "failure"
            log_entry.error_message = str(e)[:500]

        self.db.add(log_entry)
        self.db.commit()
        return log_entry

    def _check_duplicate(self, automacao_id: int, event_key: str) -> bool:
        existing = self.db.execute(
            select(AutomacaoLog).where(
                AutomacaoLog.automacao_id == automacao_id,
                AutomacaoLog.error_message == event_key,
                AutomacaoLog.executed_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            )
        ).first()
        return existing is not None

    # ── Public trigger methods ────────────────────────────────────────────────

    def trigger_card_created(self, card_id: int, card_title: str, phase_id: str, phase_name: str,
                              project_id: int, project_name: str, project_date: Optional[str] = None):
        automations = self._get_active_automations_for_trigger("card_created")
        context = self._build_context(card_id, card_title, phase_id, phase_name,
                                      project_id, project_name, project_date, "card_created")
        for a in automations:
            self._execute_webhook(a, context)

    def trigger_card_entered_phase(self, card_id: int, card_title: str, phase_id: str, phase_name: str,
                                    project_id: int, project_name: str, project_date: Optional[str] = None):
        automations = self._get_active_automations_for_trigger("card_entered_phase")
        context = self._build_context(card_id, card_title, phase_id, phase_name,
                                      project_id, project_name, project_date, "card_entered_phase")
        for a in automations:
            tcfg = a.trigger_config or {}
            if tcfg.get("phase_id") and tcfg["phase_id"] != phase_id:
                continue
            self._execute_webhook(a, context)

    def trigger_card_left_phase(self, card_id: int, card_title: str, phase_id: str, phase_name: str,
                                 project_id: int, project_name: str, project_date: Optional[str] = None):
        automations = self._get_active_automations_for_trigger("card_left_phase")
        context = self._build_context(card_id, card_title, phase_id, phase_name,
                                      project_id, project_name, project_date, "card_left_phase")
        for a in automations:
            tcfg = a.trigger_config or {}
            if tcfg.get("phase_id") and tcfg["phase_id"] != phase_id:
                continue
            self._execute_webhook(a, context)

    def trigger_card_moved(self, card_id: int, card_title: str, from_phase_id: str, from_phase_name: str,
                            to_phase_id: str, to_phase_name: str,
                            project_id: int, project_name: str, project_date: Optional[str] = None):
        automations = self._get_active_automations_for_trigger("card_moved")
        context = self._build_context(card_id, card_title, to_phase_id, to_phase_name,
                                      project_id, project_name, project_date, "card_moved")
        for a in automations:
            tcfg = a.trigger_config or {}
            from_p = tcfg.get("from_phase_id")
            to_p = tcfg.get("to_phase_id")
            if from_p and from_p != from_phase_id:
                continue
            if to_p and to_p != to_phase_id:
                continue
            self._execute_webhook(a, context)

    def trigger_card_archived(self, card_id: int, card_title: str, phase_id: str, phase_name: str,
                               project_id: int, project_name: str, project_date: Optional[str] = None):
        automations = self._get_active_automations_for_trigger("card_archived")
        context = self._build_context(card_id, card_title, phase_id, phase_name,
                                      project_id, project_name, project_date, "card_archived")
        for a in automations:
            self._execute_webhook(a, context)

    def trigger_project_date(self, project: Projeto, trigger_type: str):
        if not project.data_de_inicio:
            return
        automations = self._get_active_automations_for_trigger(trigger_type)
        if not automations:
            return
        context = {
            "card_id": project.pipefy_id,
            "card_title": project.nome or "",
            "phase_id": "",
            "phase_name": project.fase_do_pipefy or "",
            "project_id": project.pipefy_id,
            "project_name": project.nome or "",
            "project_date": project.data_de_inicio.isoformat() if project.data_de_inicio else "",
            "current_date": date.today().isoformat(),
            "event_type": trigger_type,
        }
        for a in automations:
            self._execute_webhook(a, context)

    def check_project_date_triggers(self):
        today = date.today()
        projects = self.db.query(Projeto).all()

        project_date_automations = self.db.execute(
            select(Automacao).where(
                Automacao.ativa == True,
                Automacao.trigger_type.in_(["project_days_before", "project_date_today", "project_days_after"])
            )
        ).scalars().all()

        for a in project_date_automations:
            tcfg = a.trigger_config or {}
            days = int(tcfg.get("days", 0))

            for p in projects:
                if not p.data_de_inicio:
                    continue
                diff = (p.data_de_inicio - today).days

                matched = False
                if a.trigger_type == "project_days_before" and diff == days:
                    matched = True
                elif a.trigger_type == "project_date_today" and diff == 0:
                    matched = True
                elif a.trigger_type == "project_days_after" and diff == -days:
                    matched = True

                if matched:
                    event_key = f"{a.id}:{p.pipefy_id}:{a.trigger_type}"
                    if self._check_duplicate(a.id, event_key):
                        continue
                    context = {
                        "card_id": p.pipefy_id,
                        "card_title": p.nome or "",
                        "phase_id": "",
                        "phase_name": p.fase_do_pipefy or "",
                        "project_id": p.pipefy_id,
                        "project_name": p.nome or "",
                        "project_date": p.data_de_inicio.isoformat(),
                        "current_date": today.isoformat(),
                        "event_type": a.trigger_type,
                    }
                    try:
                        self._execute_webhook(a, context)
                    except Exception as e:
                        logger.error(f"Erro ao executar automação {a.id} para projeto {p.pipefy_id}: {e}")

    def _build_context(self, card_id, card_title, phase_id, phase_name,
                        project_id, project_name, project_date, event_type):
        return {
            "card_id": card_id,
            "card_title": card_title,
            "phase_id": phase_id,
            "phase_name": phase_name,
            "project_id": project_id,
            "project_name": project_name,
            "project_date": project_date or "",
            "current_date": date.today().isoformat(),
            "event_type": event_type,
        }

    def _to_dict(self, a: Automacao) -> Dict[str, Any]:
        return {
            "id": a.id,
            "nome": a.nome,
            "descricao": a.descricao,
            "ativa": a.ativa,
            "trigger_type": a.trigger_type,
            "trigger_config": a.trigger_config or {},
            "action_type": a.action_type,
            "action_config": a.action_config or {},
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        }
