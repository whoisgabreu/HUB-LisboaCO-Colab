import uuid
from typing import List, Optional
from backend.db.json_store import JSONStore
from backend.models.kanban import KanbanConfig, KanbanPhase

class KanbanService:
    def __init__(self):
        self.store = JSONStore("kanban_configs")

    def create_kanban(self, nome: str, fases: List[KanbanPhase]) -> KanbanConfig:
        kanban = KanbanConfig(
            kanban_id=str(uuid.uuid4()),
            nome=nome,
            versao=1,
            fases=fases
        )
        self.store.insert(kanban.model_dump())
        return kanban

    def get_kanban(self, kanban_id: str) -> Optional[KanbanConfig]:
        data = self.store.find_one({"kanban_id": kanban_id})
        return KanbanConfig(**data) if data else None

    def list_kanbans(self) -> List[KanbanConfig]:
        return [KanbanConfig(**item) for item in self.store.find_all()]

    def update_kanban(self, kanban_id: str, nome: str, fases: List[KanbanPhase]) -> Optional[KanbanConfig]:
        from backend.services.exceptions import PhaseNotEmptyError
        
        existing = self.get_kanban(kanban_id)
        if not existing:
            return None

        # Identifica fases removidas
        new_phase_ids = {f.id for f in fases}
        deleted_phases = [f for f in existing.fases if f.id not in new_phase_ids]

        if deleted_phases:
            card_store = JSONStore("cards")
            for phase in deleted_phases:
                # Verifica se há cards nesta fase (pelo nome, pois cards guardam o nome)
                cards_in_phase = card_store.find_all({
                    "kanban_id": kanban_id,
                    "fase_atual": phase.nome
                })
                if cards_in_phase:
                    raise PhaseNotEmptyError(phase.nome)
        
        updated_data = {
            "nome": nome,
            "fases": [f.model_dump() for f in fases],
            "versao": existing.versao + 1
        }
        self.store.update({"kanban_id": kanban_id}, updated_data)
        return self.get_kanban(kanban_id)
