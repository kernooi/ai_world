from __future__ import annotations

import random

from autonomous_ai_world.director import DirectorAgent
from autonomous_ai_world.models import EventKind
from autonomous_ai_world.simulation import create_default_simulation


def test_director_creates_a_condition_without_moving_characters() -> None:
    simulation = create_default_simulation(seed=10)
    world = simulation.world
    locations_before = {
        character.id: character.location_id for character in world.characters.values()
    }
    director = DirectorAgent(random.Random(1), interval=1)
    world.advance_tick()

    event = director.update(world)

    assert event is not None
    assert event.kind is EventKind.SITUATION_CREATED
    assert event.actor_id is None
    assert {
        character.id: character.location_id for character in world.characters.values()
    } == locations_before
    assert event.data["feature_id"] in world.locations[event.location_id].features


def test_director_waits_for_its_interval() -> None:
    simulation = create_default_simulation(seed=10)
    director = DirectorAgent(random.Random(1), interval=3)
    simulation.world.advance_tick()

    assert director.update(simulation.world) is None

