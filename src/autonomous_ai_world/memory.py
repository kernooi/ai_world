"""Tiered character memory with salience-based retention and retrieval."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from autonomous_ai_world.models import Event, MemoryKind


@dataclass(frozen=True, slots=True)
class Memory:
    id: str
    character_id: str
    kind: MemoryKind
    content: str
    tick: int
    importance: float
    event_sequence: int
    participants: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


class MemoryStore:
    def __init__(self, character_id: str, short_term_limit: int = 12) -> None:
        self.character_id = character_id
        self.short_term_limit = short_term_limit
        self._memories: dict[str, Memory] = {}
        self._recent_ids: list[str] = []

    @property
    def all(self) -> tuple[Memory, ...]:
        return tuple(self._memories.values())

    @property
    def recent(self) -> tuple[Memory, ...]:
        return tuple(self._memories[mid] for mid in self._recent_ids if mid in self._memories)

    @property
    def long_term(self) -> tuple[Memory, ...]:
        return tuple(
            memory
            for memory in self._memories.values()
            if memory.kind in {MemoryKind.LONG_TERM, MemoryKind.EPISODIC}
        )

    def remember_event(self, event: Event, participants: tuple[str, ...] = ()) -> Memory:
        if event.importance >= 0.8:
            kind = MemoryKind.EPISODIC
        elif event.importance >= 0.6:
            kind = MemoryKind.LONG_TERM
        else:
            kind = MemoryKind.SHORT_TERM
        words = tuple(sorted(set(re.findall(r"[a-z0-9_]+", event.summary.lower()))))
        memory = Memory(
            id=f"{self.character_id}:{event.sequence}",
            character_id=self.character_id,
            kind=kind,
            content=event.summary,
            tick=event.tick,
            importance=event.importance,
            event_sequence=event.sequence,
            participants=tuple(sorted(set(participants))),
            tags=words,
        )
        self._memories[memory.id] = memory
        self._recent_ids.append(memory.id)
        while len(self._recent_ids) > self.short_term_limit:
            expired = self._recent_ids.pop(0)
            old = self._memories.get(expired)
            if old and old.kind is MemoryKind.SHORT_TERM:
                del self._memories[expired]
        return memory

    def retrieve(
        self,
        query: str,
        current_tick: int,
        *,
        participants: tuple[str, ...] = (),
        limit: int = 5,
    ) -> tuple[Memory, ...]:
        terms = set(re.findall(r"[a-z0-9_]+", query.lower()))
        participant_set = set(participants)

        def score(memory: Memory) -> float:
            overlap = len(terms.intersection(memory.tags)) / max(1, len(terms))
            social = 0.25 if participant_set.intersection(memory.participants) else 0.0
            recency = 1.0 / (1.0 + max(0, current_tick - memory.tick))
            return memory.importance * 0.5 + overlap * 0.25 + social + recency * 0.1

        ranked = sorted(self._memories.values(), key=score, reverse=True)
        return tuple(ranked[: max(0, limit)])

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "short_term_limit": self.short_term_limit,
            "recent_ids": list(self._recent_ids),
            "memories": [
                {**asdict(memory), "kind": memory.kind.value}
                for memory in self._memories.values()
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryStore:
        store = cls(str(data["character_id"]), int(data.get("short_term_limit", 12)))
        for raw in data.get("memories", []):
            memory = Memory(
                id=str(raw["id"]),
                character_id=str(raw["character_id"]),
                kind=MemoryKind(raw["kind"]),
                content=str(raw["content"]),
                tick=int(raw["tick"]),
                importance=float(raw["importance"]),
                event_sequence=int(raw["event_sequence"]),
                participants=tuple(raw.get("participants", ())),
                tags=tuple(raw.get("tags", ())),
            )
            store._memories[memory.id] = memory
        store._recent_ids = [
            memory_id
            for memory_id in data.get("recent_ids", [])
            if memory_id in store._memories
        ]
        return store


class MemoryManager:
    def __init__(self, character_ids: tuple[str, ...]) -> None:
        self.stores = {character_id: MemoryStore(character_id) for character_id in character_ids}

    def store_for(self, character_id: str) -> MemoryStore:
        return self.stores[character_id]

    def to_dict(self) -> dict[str, Any]:
        return {character_id: store.to_dict() for character_id, store in self.stores.items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryManager:
        manager = cls(tuple(data))
        manager.stores = {
            character_id: MemoryStore.from_dict(raw)
            for character_id, raw in data.items()
        }
        return manager

