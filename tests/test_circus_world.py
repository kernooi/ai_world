from __future__ import annotations

import asyncio

from autonomous_ai_world.persistence import InMemoryStateRepository
from autonomous_ai_world.simulation import Simulation, create_circus_simulation
from autonomous_ai_world.web_protocol import world_snapshot


CAST = {"pomni", "ragatha", "jax", "gangle", "kinger", "zooble"}


def test_circus_has_full_cast_and_detailed_connected_interior() -> None:
    simulation = create_circus_simulation(seed=7)

    assert set(simulation.world.characters) == CAST
    assert {character.name for character in simulation.world.characters.values()} == {
        "Pomni", "Ragatha", "Jax", "Gangle", "Kinger", "Zooble"
    }
    assert simulation.director.name == "Caine"
    assert simulation.director.once_per_day is True
    assert simulation.world.locations["main_tent"].exits == {
        "center_stage", "bedroom_hall", "dining_hall", "backstage"
    }
    assert simulation.world.locations["adventure_portal"].exits == set()


def test_caine_creates_at_most_one_director_event_each_world_day() -> None:
    simulation = create_circus_simulation(seed=9)

    async def run_schedule():
        simulation.world.advance_tick()
        first = await simulation.director.update_async(simulation.world)
        simulation.world.advance_tick()
        duplicate = await simulation.director.update_async(simulation.world)
        simulation.world.advance_tick(minutes=24 * 60)
        second_day = await simulation.director.update_async(simulation.world)
        simulation.world.advance_tick()
        second_duplicate = await simulation.director.update_async(simulation.world)
        return first, duplicate, second_day, second_duplicate

    first, duplicate, second_day, second_duplicate = asyncio.run(run_schedule())

    assert first is not None
    assert duplicate is None
    assert second_day is not None
    assert second_duplicate is None
    assert first.tick < second_day.tick


def test_caine_schedule_and_cast_survive_persistence() -> None:
    simulation = create_circus_simulation(seed=4)
    simulation.step()
    repository = InMemoryStateRepository()
    simulation.save(repository)

    restored = Simulation.load(repository, seed=4)

    assert set(restored.world.characters) == CAST
    assert restored.director.name == "Caine"
    assert restored.director.once_per_day is True
    assert restored.director.last_intervention_day == 1


def test_circus_snapshot_identifies_caine_without_leaking_hidden_key() -> None:
    snapshot = world_snapshot(create_circus_simulation(seed=3))

    assert snapshot["director"]["name"] == "Caine"
    assert snapshot["director"]["status"] == "waiting"
    assert snapshot["director"]["once_per_day"] is True
    assert snapshot["director"]["last_event_day"] is None
    assert snapshot["director"]["advanced"] is True
    assert snapshot["director"]["pacing"]["arc_stage"] == "setup"
    assert "exit_key" not in {item["id"] for item in snapshot["objects"]}
