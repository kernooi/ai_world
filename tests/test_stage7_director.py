from __future__ import annotations

import asyncio
import random

from autonomous_ai_world.ai import MockAIProvider
from autonomous_ai_world.director import DirectorAgent
from autonomous_ai_world.models import EventKind
from autonomous_ai_world.simulation import create_default_simulation


def test_async_director_observes_summary_and_generates_valid_event() -> None:
    simulation = create_default_simulation(seed=11)
    world = simulation.world
    director = DirectorAgent(random.Random(2), interval=1, provider=MockAIProvider())
    world.advance_tick()

    event = asyncio.run(director.update_async(world))

    assert event is not None
    assert event.actor_id is None
    assert event in world.events.history
    assert director.last_world_summary is not None
    assert director.last_world_summary.characters
    assert director.status == "intervened"


def test_director_cooldown_prevents_constant_intervention() -> None:
    simulation = create_default_simulation(seed=11)
    world = simulation.world
    director = DirectorAgent(random.Random(2), interval=3, provider=MockAIProvider())
    world.advance_tick()
    assert asyncio.run(director.update_async(world)) is None
    world.advance_tick()
    assert asyncio.run(director.update_async(world)) is None
    world.advance_tick()
    assert asyncio.run(director.update_async(world)) is not None
    world.advance_tick()
    assert asyncio.run(director.update_async(world)) is None


def test_invalid_director_output_preserves_world_state() -> None:
    provider = MockAIProvider(responses=[{"kind": "castle", "title": "Impossible"}])
    simulation = create_default_simulation(seed=11)
    world = simulation.world
    director = DirectorAgent(random.Random(2), interval=1, provider=provider)
    world.advance_tick()
    object_ids = set(world.objects)
    weather = world.weather

    event = asyncio.run(director.update_async(world))

    assert event is None
    assert set(world.objects) == object_ids
    assert world.weather is weather
    assert director.status == "provider_failed_no_intervention"
    assert not [item for item in world.events.history if item.actor_id is None]


def test_director_event_is_perceived_but_does_not_assign_character_action() -> None:
    simulation = create_default_simulation(seed=7, enable_adventures=False)
    simulation.run(3)
    director_events = [
        event for event in simulation.world.events.history if event.actor_id is None
    ]

    assert len(director_events) == 1
    assert director_events[0].kind in {
        EventKind.SITUATION_CREATED,
        EventKind.WEATHER_CHANGED,
        EventKind.ENVIRONMENT_CHANGED,
    }
    assert all(character.last_action.actor_id == character.id for character in simulation.world.characters.values())


def test_stage7_loop_director_creates_condition_and_characters_choose_response() -> None:
    simulation = create_default_simulation(seed=7, enable_adventures=False)
    simulation.step()
    simulation.step()

    events = simulation.step()
    director_event = next(event for event in events if event.actor_id is None)
    feature_id = director_event.data.get("feature_id")
    reactions = [
        event
        for event in events
        if event.actor_id is not None
        and event.sequence > director_event.sequence
        and event.data.get("target_id") == feature_id
    ]

    assert director_event.kind is EventKind.SITUATION_CREATED
    assert reactions
    assert all(reaction.actor_id in simulation.world.characters for reaction in reactions)
    assert all(
        simulation.world.characters[reaction.actor_id].current_intention is not None
        for reaction in reactions
    )
