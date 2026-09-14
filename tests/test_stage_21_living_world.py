from __future__ import annotations

import math

from autonomous_ai_world.models import Action, ActionKind
from autonomous_ai_world.persistence import InMemoryStateRepository
from autonomous_ai_world.simulation import Simulation, create_circus_simulation, create_default_simulation
from autonomous_ai_world.web_protocol import world_snapshot


def test_circus_snapshot_exposes_authoritative_positions_and_activity_spots() -> None:
    simulation = create_circus_simulation(seed=21)
    simulation.step()
    public = world_snapshot(simulation)

    assert public["living_world"]["enabled"] is True
    assert len(public["living_world"]["activity_spots"]) >= 45
    pomni = next(item for item in public["characters"] if item["id"] == "pomni")
    assert pomni["spatial"]["location_id"] == pomni["location_id"]
    assert set(pomni["spatial"]["position"]) == {"x", "z"}
    assert pomni["spatial"]["plan"]


def test_routine_moves_toward_a_stable_target_and_contains_multiple_steps() -> None:
    simulation = create_circus_simulation(seed=22, enable_adventures=False)
    living = simulation.living_world
    state = living.characters["pomni"]
    living.advance(simulation.world, [Action("pomni", ActionKind.EXPLORE)])
    assert len(state.plan) >= 2
    target = state.plan[0]
    first_distance = math.hypot(state.x - target.x, state.z - target.z)

    living.advance(simulation.world)
    second_distance = math.hypot(state.x - target.x, state.z - target.z)
    assert second_distance <= first_distance
    assert state.phase in {"walking", "acting"}


def test_spatial_state_and_current_routine_survive_save_and_load() -> None:
    simulation = create_circus_simulation(seed=23, enable_adventures=False)
    simulation.run(4)
    before = simulation.living_world.public_state()["characters"]
    repository = InMemoryStateRepository()
    simulation.save(repository)

    restored = Simulation.load(repository, seed=23)
    after = restored.living_world.public_state()["characters"]
    assert after == before


def test_new_director_worlds_automatically_receive_four_affordances() -> None:
    simulation = create_circus_simulation(seed=24)
    simulation.step()
    adventure = next(iter(simulation.world.adventures.values()))
    simulation.living_world.advance(simulation.world)

    for location_id in adventure.generated_location_ids:
        spots = [
            spot for spot in simulation.living_world.spots.values()
            if spot.location_id == location_id
        ]
        assert {spot.kind for spot in spots} == {"travel", "curiosity", "adventure", "rest"}


def test_activity_context_is_available_to_mock_and_future_real_ai() -> None:
    circus = create_circus_simulation(seed=25, enable_adventures=False)
    perception = circus.world.perceive("pomni")
    assert perception.available_activity_spots
    assert perception.current_activity
    assert "zooble" in perception.nearby_distances

    classic = create_default_simulation(seed=25, enable_adventures=False)
    assert classic.world.perceive("alice").available_activity_spots == ()


def test_busy_cast_finishes_routines_before_requesting_another_decision() -> None:
    simulation = create_circus_simulation(seed=26, enable_adventures=False)
    simulation.step()
    busy = {agent.character_id for agent in simulation.agents if simulation.living_world.is_busy(agent.character_id)}
    before = {agent.character_id: len(agent.provider.calls) for agent in simulation.agents}  # type: ignore[attr-defined]
    assert busy

    simulation.step()
    after = {agent.character_id: len(agent.provider.calls) for agent in simulation.agents}  # type: ignore[attr-defined]
    assert all(after[character_id] == before[character_id] for character_id in busy)


def test_social_routine_keeps_its_physical_conversation_target() -> None:
    simulation = create_circus_simulation(seed=27, enable_adventures=False)
    simulation.living_world.advance(
        simulation.world, [Action("pomni", ActionKind.TALK, "zooble", "Can we compare notes?")]
    )
    public = simulation.living_world.public_state()["characters"]["pomni"]
    assert public["target_id"] == "zooble"
    assert public["plan"][0]["activity"] == "approaching"


def test_browser_consumes_server_positions_instead_of_random_idle_wandering() -> None:
    from pathlib import Path

    script = (Path(__file__).parents[1] / "src" / "autonomous_ai_world" / "web" / "app.js").read_text(encoding="utf-8")
    assert "syncSpatialCharacter" in script
    assert "view.spatialControlled" in script
    assert "activityTargetId" in script
    assert "syncActivitySpots" in script
