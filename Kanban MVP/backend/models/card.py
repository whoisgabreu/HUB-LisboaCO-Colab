from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class CardPhaseSnapshot(BaseModel):
    fase_id: str
    dados: Dict[str, Any]
    criado_em: datetime = Field(default_factory=datetime.now)

class CardHistoryEntry(BaseModel):
    fase: str
    entrada: datetime
    saida: Optional[datetime] = None

class Card(BaseModel):
    card_id: str
    kanban_id: str
    titulo: str = "Novo Card"
    fase_atual: str
    fases: List[CardPhaseSnapshot] = []
    historico: List[CardHistoryEntry] = []
    criado_em: datetime = Field(default_factory=datetime.now)
    atualizado_em: datetime = Field(default_factory=datetime.now)

class CardCreate(BaseModel):
    kanban_id: str
    dados_iniciais: Dict[str, Any] = {}

class CardUpdate(BaseModel):
    dados: Dict[str, Any]

class CardMove(BaseModel):
    nova_fase_id: str
    dados: Optional[Dict[str, Any]] = None
