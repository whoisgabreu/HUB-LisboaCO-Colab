from pydantic import BaseModel, Field
from typing import List, Optional

class KanbanField(BaseModel):
    id: str
    label: str
    tipo: str  # string, text, number, boolean, datetime, select
    obrigatorio: bool = False
    readonly: bool = False
    opcoes: Optional[List[str]] = None

class KanbanPhase(BaseModel):
    id: str
    nome: str
    ordem: int
    campos: List[KanbanField]
    permite_acesso_direto: bool = False

class KanbanConfig(BaseModel):
    kanban_id: str
    nome: str
    versao: int = 1
    fases: List[KanbanPhase]

class KanbanConfigCreate(BaseModel):
    nome: str
    fases: List[KanbanPhase]
