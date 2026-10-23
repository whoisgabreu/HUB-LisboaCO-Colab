"""Small adapter that stores checklist hierarchy without changing the schema.

The parent id is encoded in the existing ``observacao`` field and removed again
before the value reaches the template. Database services and task rules remain
unchanged; this module only adds presentation metadata.
"""

from __future__ import annotations

import re


_PARENT_MARKER = re.compile(r"^\s*\[\[tech-parent:(\d+)\]\](?:\r?\n|$)")


def split_observation(value):
    """Return ``(parent_id, visible_text)`` for a stored observation."""
    text = str(value or "")
    match = _PARENT_MARKER.match(text)
    if not match:
        return None, text.strip() or None
    visible = text[match.end() :].strip()
    return int(match.group(1)), visible or None


def merge_observation(value, parent_id=None):
    """Encode a parent id while preserving only the user-visible observation."""
    _old_parent, visible = split_observation(value)
    try:
        normalized_parent = int(parent_id) if parent_id not in (None, "") else None
    except (TypeError, ValueError):
        normalized_parent = None
    if not normalized_parent or normalized_parent < 1:
        return visible
    marker = f"[[tech-parent:{normalized_parent}]]"
    return f"{marker}\n{visible}" if visible else marker


def validate_parent(stages, parent_id=None, stage_id=None):
    """Validate a one-level parent relation inside the current project."""
    if parent_id in (None, ""):
        return None
    try:
        candidate_id = int(parent_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Selecione uma tarefa mãe válida.") from exc

    current_id = int(stage_id) if stage_id not in (None, "") else None
    if candidate_id < 1 or candidate_id == current_id:
        raise ValueError("Uma tarefa não pode ser mãe dela mesma.")

    sources = list(stages or [])
    by_id = {stage.get("id"): stage for stage in sources}
    candidate = by_id.get(candidate_id)
    if not candidate:
        raise ValueError("A tarefa mãe precisa pertencer a este projeto.")

    candidate_parent, _visible = split_observation(candidate.get("observacao"))
    if candidate_parent:
        raise ValueError("Uma subtarefa não pode receber outra subtarefa.")

    if current_id:
        has_children = any(
            split_observation(stage.get("observacao"))[0] == current_id
            for stage in sources
            if stage.get("id") != current_id
        )
        if has_children:
            raise ValueError(
                "Mova as subtarefas antes de transformar esta tarefa em subtarefa."
            )

    return candidate_id


def arrange_stages(stages):
    """Return copied stages ordered as parents followed by their subtasks."""
    sources = list(stages or [])
    prepared = []
    by_id = {}

    for source in sources:
        stage = dict(source)
        parent_id, visible = split_observation(stage.get("observacao"))
        stage["observacao"] = visible
        stage["_parent_id"] = parent_id
        stage["_parent_name"] = None
        stage["_hierarchy_level"] = 0
        stage["_subtask_count"] = 0
        stage["_subtasks_completed"] = 0
        stage["_subtask_progress_pct"] = 0
        stage["_has_open_subtasks"] = False
        stage["_display_status"] = stage.get("status")
        stage["_status_derived"] = False
        stage["_hierarchy_active"] = False
        stage["_can_move_up"] = False
        stage["_can_move_down"] = False
        prepared.append(stage)
        by_id[stage.get("id")] = stage

    for stage in prepared:
        parent_id = stage.get("_parent_id")
        if parent_id == stage.get("id") or parent_id not in by_id:
            stage["_parent_id"] = None

    # Break malformed cycles defensively. The UI only offers root stages as parents,
    # but old/manual payloads must never make the checklist disappear.
    for stage in prepared:
        seen = {stage.get("id")}
        current = stage.get("_parent_id")
        while current:
            if current in seen:
                stage["_parent_id"] = None
                break
            seen.add(current)
            parent = by_id.get(current)
            current = parent.get("_parent_id") if parent else None

    children = {}
    for stage in prepared:
        parent_id = stage.get("_parent_id")
        if parent_id:
            children.setdefault(parent_id, []).append(stage)

    for stage in prepared:
        stage_children = children.get(stage.get("id"), [])
        stage["_subtask_count"] = len(stage_children)
        stage["_subtasks_completed"] = sum(
            1 for child in stage_children if child.get("status") == "concluida"
        )
        stage["_subtask_progress_pct"] = (
            round(stage["_subtasks_completed"] / len(stage_children) * 100)
            if stage_children
            else 0
        )
        stage["_has_open_subtasks"] = any(
            child.get("status") != "concluida" for child in stage_children
        )
        if stage_children:
            stage["_status_derived"] = True
            if stage["_subtasks_completed"] == len(stage_children):
                stage["_display_status"] = "concluida"
            elif stage["_subtasks_completed"] or any(
                child.get("status") == "em_andamento" for child in stage_children
            ):
                stage["_display_status"] = "em_andamento"
            else:
                stage["_display_status"] = "pendente"
        stage["_hierarchy_active"] = bool(children)

    roots = [stage for stage in prepared if not stage.get("_parent_id")]
    for siblings in [roots, *children.values()]:
        for index, stage in enumerate(siblings):
            stage["_can_move_up"] = index > 0
            stage["_can_move_down"] = index < len(siblings) - 1

    ordered = []
    visited = set()

    def append_branch(stage, level=0):
        stage_id = stage.get("id")
        if stage_id in visited:
            return
        visited.add(stage_id)
        stage["_hierarchy_level"] = level
        parent = by_id.get(stage.get("_parent_id"))
        stage["_parent_name"] = parent.get("nome") if parent else None
        ordered.append(stage)
        for child in children.get(stage_id, []):
            append_branch(child, level + 1)

    for stage in prepared:
        if not stage.get("_parent_id"):
            append_branch(stage)
    for stage in prepared:
        append_branch(stage)

    return ordered


def reorder_stage_ids(stages, stage_id, direction):
    """Return a hierarchy-safe visual order after moving one sibling."""
    arranged = arrange_stages(stages)
    try:
        normalized_id = int(stage_id)
    except (TypeError, ValueError):
        return [stage.get("id") for stage in arranged]

    by_id = {stage.get("id"): stage for stage in arranged}
    target = by_id.get(normalized_id)
    if not target:
        return [stage.get("id") for stage in arranged]

    roots = [stage for stage in arranged if not stage.get("_parent_id")]
    children = {}
    for stage in arranged:
        parent_id = stage.get("_parent_id")
        if parent_id:
            children.setdefault(parent_id, []).append(stage)

    parent_id = target.get("_parent_id")
    siblings = roots if not parent_id else children.get(parent_id, [])
    current_index = next(
        (index for index, stage in enumerate(siblings) if stage.get("id") == normalized_id),
        None,
    )
    if current_index is None:
        return [stage.get("id") for stage in arranged]

    next_index = current_index - 1 if direction == "cima" else current_index + 1
    if next_index < 0 or next_index >= len(siblings):
        return [stage.get("id") for stage in arranged]
    siblings[current_index], siblings[next_index] = siblings[next_index], siblings[current_index]

    ordered_ids = []
    visited = set()

    def append_branch(stage):
        stage_key = stage.get("id")
        if stage_key in visited:
            return
        visited.add(stage_key)
        ordered_ids.append(stage_key)
        for child in children.get(stage_key, []):
            append_branch(child)

    for root in roots:
        append_branch(root)
    for stage in arranged:
        append_branch(stage)
    return ordered_ids
