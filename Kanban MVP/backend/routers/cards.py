from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from backend.models.card import Card, CardCreate, CardUpdate, CardMove
from backend.services.card_service import CardService, PhaseTransitionError
from backend.services.kanban_service import KanbanService

router = APIRouter(prefix="/cards", tags=["cards"])
kanban_service = KanbanService()
service = CardService(kanban_service)

@router.post("", response_model=Card)
def create_card(card_in: CardCreate):
    card = service.create_card(card_in.kanban_id, card_in.dados_iniciais)
    if not card:
        raise HTTPException(status_code=400, detail="Could not create card. Check kanban_id.")
    return card

@router.get("", response_model=List[Card])
def list_cards(kanban_id: Optional[str] = Query(None)):
    return service.list_cards(kanban_id)

@router.get("/{card_id}", response_model=Card)
def get_card(card_id: str):
    card = service.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card

@router.put("/{card_id}", response_model=Card)
def update_card(card_id: str, card_update: CardUpdate):
    card = service.update_current_phase_data(card_id, card_update.dados)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card

@router.post("/{card_id}/mover", response_model=Card)
def move_card(card_id: str, card_move: CardMove):
    try:
        card = service.move_card(card_id, card_move.nova_fase_id, card_move.dados)
    except PhaseTransitionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card

@router.delete("/{card_id}")
def delete_card(card_id: str):
    print(f"Tentando deletar card: {card_id}")
    success = service.delete_card(card_id)
    if not success:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"message": "Card deleted successfully"}
