"""Deterministic, directional relationship updates derived from world events."""

from __future__ import annotations

from autonomous_ai_world.models import Character, Event, EventKind, Relationship


class RelationshipManager:
    def __init__(self, characters: dict[str, Character]) -> None:
        self.characters = characters
        for owner in characters.values():
            for target_id in characters:
                if target_id != owner.id:
                    owner.relationships.setdefault(target_id, Relationship())

    def get(self, owner_id: str, target_id: str) -> Relationship:
        return self.characters[owner_id].relationships[target_id]

    def process(self, event: Event) -> None:
        target_id = event.data.get("target_id")
        if not event.actor_id or not isinstance(target_id, str):
            return
        if target_id not in self.characters or event.actor_id not in self.characters:
            return
        target_view = self.get(target_id, event.actor_id)
        if event.kind is EventKind.HELPED:
            target_view.adjust(trust=0.12, friendship=0.1, respect=0.08, anger=-0.08)
        elif event.kind is EventKind.LIED:
            target_view.adjust(trust=-0.18, suspicion=0.2, anger=0.12, respect=-0.05)
        elif event.kind is EventKind.SPOKE:
            target_view.adjust(friendship=0.015, trust=0.005)

