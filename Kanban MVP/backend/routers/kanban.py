from fastapi import APIRouter, HTTPException
from typing import List
from backend.models.kanban import KanbanConfig, KanbanConfigCreate, KanbanPhase
from backend.services.kanban_service import KanbanService

router = APIRouter(prefix="/kanban", tags=["kanban"])
service = KanbanService()

@router.post("", response_model=KanbanConfig)
def create_kanban(config: KanbanConfigCreate):
    return service.create_kanban(config.nome, config.fases)

@router.get("", response_model=List[KanbanConfig])
def list_kanbans():
    return service.list_kanbans()

@router.get("/{kanban_id}", response_model=KanbanConfig)
def get_kanban(kanban_id: str):
    kanban = service.get_kanban(kanban_id)
    if not kanban:
        raise HTTPException(status_code=404, detail="Kanban not found")
    return kanban

@router.put("/{kanban_id}", response_model=KanbanConfig)
def update_kanban(kanban_id: str, config: KanbanConfigCreate):
    from backend.services.exceptions import PhaseNotEmptyError
    try:
        kanban = service.update_kanban(kanban_id, config.nome, config.fases)
    except PhaseNotEmptyError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    if not kanban:
        raise HTTPException(status_code=404, detail="Kanban not found")
    return kanban
