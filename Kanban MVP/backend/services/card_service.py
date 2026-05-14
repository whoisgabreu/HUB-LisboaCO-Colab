import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from backend.db.json_store import JSONStore
from backend.models.card import Card, CardPhaseSnapshot, CardHistoryEntry
from backend.models.kanban import KanbanConfig, KanbanPhase
from backend.services.kanban_service import KanbanService


class PhaseTransitionError(Exception):
    """Raised when a card movement violates the deterministic phase transition rules."""
    pass

class CardService:
    def __init__(self, kanban_service: KanbanService):
        self.store = JSONStore("cards")
        self.kanban_service = kanban_service

    def create_card(self, kanban_id: str, dados_iniciais: Dict[str, Any]) -> Optional[Card]:
        kanban = self.kanban_service.get_kanban(kanban_id)
        if not kanban or not kanban.fases:
            return None

        primeira_fase = sorted(kanban.fases, key=lambda x: x.ordem)[0]
        now = datetime.now()
        
        # Pega o título dos dados iniciais ou usa um padrão
        titulo = dados_iniciais.get('titulo') or dados_iniciais.get('nome') or "Novo Card"

        # Injeta _labels para auditoria
        labels = {campo.id: campo.label for campo in primeira_fase.campos}
        dados_com_labels = {**dados_iniciais, "_labels": labels}

        card = Card(
            card_id=str(uuid.uuid4()),
            kanban_id=kanban_id,
            titulo=str(titulo),
            fase_atual=primeira_fase.nome,
            fases=[
                CardPhaseSnapshot(fase_id=primeira_fase.nome, dados=dados_com_labels, criado_em=now)
            ],
            historico=[
                CardHistoryEntry(fase=primeira_fase.nome, entrada=now)
            ],
            criado_em=now,
            atualizado_em=now
        )
        self.store.insert(card.model_dump())
        return card

    def get_card(self, card_id: str) -> Optional[Card]:
        data = self.store.find_one({"card_id": card_id})
        return Card(**data) if data else None

    def list_cards(self, kanban_id: str = None) -> List[Card]:
        query = {"kanban_id": kanban_id} if kanban_id else {}
        return [Card(**item) for item in self.store.find_all(query)]

    def update_current_phase_data(self, card_id: str, dados: Dict[str, Any]) -> Optional[Card]:
        card = self.get_card(card_id)
        if not card:
            return None

        # Update the latest snapshot in the fases array
        # Note: We update the CURRENT phase snapshot, but we don't touch previous ones.
        # However, the requirement says "Never edit directly a past phase". 
        # Updating the current phase's data before moving to the next is generally allowed in MVP.
        # Once moved, it becomes "past".
        
        # Só atualizamos o título raiz se estivermos na PRIMEIRA fase do kanban
        # Isso evita que campos de fases futuras (que podem ter o ID 'titulo' mas outro propósito) sobrescrevam o nome do projeto
        kanban = self.kanban_service.get_kanban(card.kanban_id)
        is_first_phase = False
        if kanban and kanban.fases:
            primeira_fase = sorted(kanban.fases, key=lambda x: x.ordem)[0]
            if card.fase_atual == primeira_fase.nome:
                is_first_phase = True

        for snapshot in card.fases:
            if snapshot.fase_id == card.fase_atual:
                snapshot.dados.update(dados)
                if is_first_phase and 'titulo' in dados:
                    card.titulo = str(dados['titulo'])
                break
        
        card.atualizado_em = datetime.now()
        self.store.update({"card_id": card_id}, card.model_dump())
        return card

    def move_card(self, card_id: str, nova_fase_id: str, dados_nova_fase: Dict[str, Any] = None) -> Optional[Card]:
        card = self.get_card(card_id)
        if not card:
            return None

        now = datetime.now()
        kanban = self.kanban_service.get_kanban(card.kanban_id)
        if not kanban:
            return None

        target_fase = next((f for f in kanban.fases if f.id == nova_fase_id), None)
        if not target_fase:
            # Fallback: maybe nova_fase_id is already a name?
            target_fase = next((f for f in kanban.fases if f.nome == nova_fase_id), None)

        if not target_fase:
            return None

        # ── Regra de Transição Determinística ──────────────────────────────────
        # Encontra a fase atual pelo nome para obter a ordem
        current_fase = next(
            (f for f in kanban.fases if f.nome == card.fase_atual), None
        )

        if current_fase and current_fase.id != target_fase.id:
            is_direct_access = target_fase.permite_acesso_direto
            is_next_in_sequence = target_fase.ordem == current_fase.ordem + 1
            # Permite retorno se o card já passou por essa fase (existe snapshot)
            already_visited = any(s.fase_id == target_fase.nome for s in card.fases)

            if not is_direct_access and not is_next_in_sequence and not already_visited:
                raise PhaseTransitionError(
                    f"Transição bloqueada: card está na fase '{current_fase.nome}' "
                    f"(ordem {current_fase.ordem}). A fase destino '{target_fase.nome}' "
                    f"não é a próxima, não é um retorno ao histórico e não "
                    f"possui 'permite_acesso_direto' habilitado."
                )
        # ────────────────────────────────────────────────────────────────────────

        nova_fase_nome = target_fase.nome
        
        # Close current history entry
        for entry in card.historico:
            if entry.fase == card.fase_atual and entry.saida is None:
                entry.saida = now
                break

        # Update fase_atual
        card.fase_atual = nova_fase_nome
        
        # Reiniciamos os dados da nova fase como um objeto limpo (sem duplicar dados anteriores conforme solicitado)
        dados = dados_nova_fase or {}
        
        # Injeta _labels para auditoria na nova fase
        labels = {campo.id: campo.label for campo in target_fase.campos}
        dados["_labels"] = labels
        
        # Update or add snapshot
        existing_snapshot = next((s for s in card.fases if s.fase_id == nova_fase_nome), None)
        if existing_snapshot:
            existing_snapshot.dados = dados
            existing_snapshot.criado_em = now
        else:
            card.fases.append(CardPhaseSnapshot(fase_id=nova_fase_nome, dados=dados, criado_em=now))
        
        # Add new history entry
        card.historico.append(CardHistoryEntry(fase=nova_fase_nome, entrada=now))
        
        card.atualizado_em = now
        self.store.update({"card_id": card_id}, card.model_dump())
        return card

    def delete_card(self, card_id: str) -> bool:
        return self.store.delete({"card_id": card_id})
