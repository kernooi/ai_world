from __future__ import annotations

from autonomous_ai_world.memory import MemoryKind, MemoryStore
from autonomous_ai_world.models import Event, EventKind


def event(sequence: int, summary: str, importance: float, tick: int = 1) -> Event:
    return Event(sequence, tick, EventKind.HELPED, "bob", "forest", summary, {}, importance)


def test_important_event_becomes_persistent_episodic_memory() -> None:
    store = MemoryStore("alice")

    memory = store.remember_event(event(1, "Bob saved Alice during a storm.", 0.9), ("bob",))

    assert memory.kind is MemoryKind.EPISODIC
    assert memory in store.long_term


def test_routine_short_term_memories_expire_but_important_ones_remain() -> None:
    store = MemoryStore("alice", short_term_limit=2)
    important = store.remember_event(event(1, "A major discovery.", 0.8))
    store.remember_event(event(2, "Routine one.", 0.2))
    store.remember_event(event(3, "Routine two.", 0.2))
    store.remember_event(event(4, "Routine three.", 0.2))

    assert important in store.all
    assert len(store.recent) == 2
    assert all(memory.content != "Routine one." for memory in store.all)


def test_retrieval_prefers_relevant_social_memory() -> None:
    store = MemoryStore("alice")
    store.remember_event(event(1, "Charlie found a stone.", 0.6), ("charlie",))
    expected = store.remember_event(
        event(2, "Bob helped Alice during danger.", 0.8, tick=2), ("bob",)
    )

    retrieved = store.retrieve("help danger", 10, participants=("bob",), limit=1)

    assert retrieved == (expected,)


def test_memory_store_round_trips_all_memory_tiers() -> None:
    store = MemoryStore("alice")
    store.remember_event(event(1, "Routine.", 0.2))
    store.remember_event(event(2, "Important.", 0.7))
    store.remember_event(event(3, "Defining moment.", 0.95))

    restored = MemoryStore.from_dict(store.to_dict())

    assert restored.all == store.all
    assert restored.recent == store.recent
