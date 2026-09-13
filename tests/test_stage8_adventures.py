from __future__ import annotations

import asyncio
import random

import pytest

from autonomous_ai_world.adventures import AdventureManager
from autonomous_ai_world.ai import MockAIProvider
from autonomous_ai_world.models import (
    AdventurePhase,
    AdventureStatus,
    EventKind,
)
from autonomous_ai_world.persistence import InMemoryStateRepository
from autonomous_ai_world.simulation import Simulation, create_default_simulation


def test_full_adventure_emerges_from_independent_character_actions() -> None:
    simulation = create_default_simulation(seed=7)

    simulation.run(7)

    adventure = next(iter(simulation.world.adventures.values()))
    assert adventure.title == "The Echo Below"
    assert adventure.phase is AdventurePhase.RESOLUTION
    assert adventure.status is AdventureStatus.RESOLVED
    assert adventure.resolved_by == "alice"
    assert adventure.participants == {"alice", "charlie"}
    assert adventure.outcome is not None
    assert "observatory" in simulation.world.locations[adventure.origin_location_id].exits


def test_adventure_outcome_is_not_locked_to_one_character() -> None:
    resolvers: set[str | None] = set()
    for seed in range(6):
        simulation = create_default_simulation(seed=seed)
        simulation.run(20)
        adventure = next(iter(simulation.world.adventures.values()))
        resolvers.add(adventure.resolved_by)

    assert None not in resolvers
    assert len(resolvers) >= 2


def test_each_phase_has_a_prior_causal_character_event() -> None:
    simulation = create_default_simulation(seed=7)
    simulation.run(7)
    events = {event.sequence: event for event in simulation.world.events.history}
    progress = [
        event
        for event in events.values()
        if event.kind in {EventKind.ADVENTURE_PROGRESSED, EventKind.ADVENTURE_RESOLVED}
    ]

    assert [event.data["phase"] for event in progress] == [
        "investigation",
        "discovery",
        "escalation",
        "resolution",
    ]
    for event in progress:
        cause = events[event.data["cause_event_sequence"]]
        assert cause.sequence < event.sequence
        assert cause.actor_id == event.actor_id
        assert cause.kind in {
            EventKind.INSPECTED,
            EventKind.OBJECT_DISCOVERED,
            EventKind.MOVED,
        }


def test_adventure_start_respects_information_asymmetry() -> None:
    simulation = create_default_simulation(seed=7)

    simulation.run(3)

    adventure = next(iter(simulation.world.adventures.values()))
    assert adventure.origin_location_id == "forest"
    assert f"adventure:{adventure.id}" in simulation.world.characters["charlie"].knowledge
    assert f"adventure:{adventure.id}" not in simulation.world.characters["alice"].knowledge
    assert f"adventure:{adventure.id}" not in simulation.world.characters["bob"].knowledge
    assert "observatory" not in simulation.world.locations["forest"].exits


def test_discovery_opens_hidden_location_authoritatively() -> None:
    simulation = create_default_simulation(seed=7)
    simulation.run(3)
    adventure = next(iter(simulation.world.adventures.values()))

    simulation.step()

    assert adventure.phase is AdventurePhase.DISCOVERY
    assert adventure.hidden_location_id in simulation.world.locations[adventure.origin_location_id].exits
    assert adventure.origin_location_id in simulation.world.locations[adventure.hidden_location_id].exits


def test_world_rejects_phase_skip_without_mutating_adventure() -> None:
    simulation = create_default_simulation(seed=7)
    simulation.run(3)
    adventure = next(iter(simulation.world.adventures.values()))
    phase_before = adventure.phase

    with pytest.raises(ValueError, match="invalid adventure transition"):
        simulation.world.advance_adventure(
            adventure.id,
            AdventurePhase.RESOLUTION,
            actor_id="alice",
            cause_event_sequence=1,
        )

    assert adventure.phase is phase_before
    assert adventure.status is AdventureStatus.ACTIVE


def test_invalid_causal_event_cannot_advance_phase() -> None:
    simulation = create_default_simulation(seed=7)
    simulation.run(3)
    adventure = next(iter(simulation.world.adventures.values()))
    assert adventure.phase is AdventurePhase.INVESTIGATION

    with pytest.raises(ValueError, match="causal event"):
        simulation.world.advance_adventure(
            adventure.id,
            AdventurePhase.DISCOVERY,
            actor_id="charlie",
            cause_event_sequence=3,
        )

    assert adventure.phase is AdventurePhase.INVESTIGATION


def test_in_progress_adventure_persists_and_continues_after_load() -> None:
    simulation = create_default_simulation(seed=7)
    simulation.run(4)
    repository = InMemoryStateRepository()
    simulation.save(repository)

    restored = Simulation.load(repository, seed=7)
    before = next(iter(restored.world.adventures.values()))
    assert before.phase is AdventurePhase.DISCOVERY
    assert restored.adventures is not None

    restored.run(10)

    after = next(iter(restored.world.adventures.values()))
    assert after.status is AdventureStatus.RESOLVED
    assert after.outcome


def test_director_summary_tracks_unresolved_adventure() -> None:
    simulation = create_default_simulation(seed=7)

    simulation.run(4)

    summary = simulation.director.last_world_summary
    assert summary is not None
    assert summary.active_adventures
    assert summary.active_adventures[0]["phase"] in {
        "hook",
        "investigation",
        "discovery",
    }


def test_invalid_mock_adventure_selection_does_not_create_world_state() -> None:
    simulation = create_default_simulation(seed=1, enable_adventures=False)
    manager = AdventureManager(random.Random(1))
    provider = MockAIProvider(
        responses=[{"template_id": "invented", "origin_location_id": "cave"}]
    )
    simulation.world.advance_tick()

    result = asyncio.run(
        manager.maybe_start(
            simulation.world,
            provider,
            {"activity_score": 0.0},
            timeout_seconds=1,
        )
    )

    assert result is None
    assert not simulation.world.adventures
    assert manager.last_error is not None


def test_unresolved_adventure_can_expire_without_forcing_characters() -> None:
    simulation = create_default_simulation(seed=7)
    simulation.run(3)
    assert simulation.adventures is not None
    simulation.adventures.max_idle_ticks = 2
    adventure = simulation.adventures.active
    assert adventure is not None

    simulation.world.advance_tick()
    simulation.world.advance_tick()
    event = simulation.adventures.maintain(simulation.world)

    assert event is not None
    assert event.kind is EventKind.ADVENTURE_EXPIRED
    assert adventure.status is AdventureStatus.EXPIRED
    assert adventure.resolved_by is None
