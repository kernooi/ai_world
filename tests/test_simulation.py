from __future__ import annotations

from autonomous_ai_world.models import EventKind
from autonomous_ai_world.simulation import create_default_simulation


def test_each_character_acts_once_per_tick() -> None:
    simulation = create_default_simulation(seed=12)

    events = simulation.step()

    assert len(events) == 3
    assert {event.actor_id for event in events} == {"alice", "bob", "charlie"}
    assert all(event.kind is not EventKind.ACTION_REJECTED for event in events)


def test_director_adds_an_event_every_third_tick() -> None:
    simulation = create_default_simulation(seed=12, enable_adventures=False)

    simulation.run(3)

    director_events = [
        event
        for event in simulation.world.events.history
        if event.kind is EventKind.SITUATION_CREATED
    ]
    assert len(director_events) == 1
    assert director_events[0].tick == 3


def test_same_seed_produces_a_repeatable_world_history() -> None:
    first = create_default_simulation(seed=99)
    second = create_default_simulation(seed=99)

    first.run(8)
    second.run(8)

    assert [event.summary for event in first.world.events.history] == [
        event.summary for event in second.world.events.history
    ]


def test_long_run_keeps_actions_valid_and_characters_energized() -> None:
    simulation = create_default_simulation(seed=123)

    events = simulation.run(50)

    assert not [event for event in events if event.kind is EventKind.ACTION_REJECTED]
    assert all(
        0 <= character.energy <= character.max_energy
        for character in simulation.world.characters.values()
    )
