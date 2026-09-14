from __future__ import annotations

from pathlib import Path

from autonomous_ai_world.models import AdventureStatus, EventKind
from autonomous_ai_world.persistence import InMemoryStateRepository
from autonomous_ai_world.simulation import Simulation, create_circus_simulation
from autonomous_ai_world.web_protocol import world_snapshot


WEB_SCRIPT = (
    Path(__file__).parents[1] / "src" / "autonomous_ai_world" / "web" / "app.js"
).read_text(encoding="utf-8")


def test_caine_creates_a_distinct_quest_world_every_world_day() -> None:
    simulation = create_circus_simulation(seed=8)
    simulation.run(241)
    adventures = list(simulation.world.adventures.values())

    assert [adventure.created_day for adventure in adventures] == [1, 2, 3]
    assert len({adventure.world_theme for adventure in adventures}) == 3
    assert all(len(adventure.generated_location_ids) == 3 for adventure in adventures)
    assert len({location_id for adventure in adventures for location_id in adventure.generated_location_ids}) == 9
    assert all(len(adventure.objectives) == 4 for adventure in adventures)
    starts = [event for event in simulation.world.events.history if event.kind is EventKind.ADVENTURE_STARTED]
    assert starts[0].tick == 1
    assert starts[1].tick >= 96  # An active climax may finish after midnight.
    assert starts[2].tick == 240


def test_caine_announcement_reaches_cast_and_objectives_are_completed_by_characters() -> None:
    simulation = create_circus_simulation(seed=7)
    simulation.step()
    adventure = next(iter(simulation.world.adventures.values()))

    assert all(f"adventure:{adventure.id}" in character.knowledge for character in simulation.world.characters.values())
    # Spatial routines let the cast visibly approach and perform each action,
    # so a complete five-phase adventure intentionally takes longer.
    simulation.run(100)
    assert adventure.status is AdventureStatus.RESOLVED
    assert all(objective.status == "complete" for objective in adventure.objectives)
    assert all(objective.completed_by in simulation.world.characters for objective in adventure.objectives)


def test_public_snapshot_contains_generated_world_and_quest_contract() -> None:
    simulation = create_circus_simulation(seed=9)
    simulation.step()
    snapshot = world_snapshot(simulation)
    adventure = snapshot["adventures"][0]
    pocket_locations = [location for location in snapshot["locations"] if location.get("adventure_id") == adventure["id"]]

    assert adventure["quest_objective"]
    assert len(adventure["objectives"]) == 4
    assert len(pocket_locations) == 3
    assert [location["zone_index"] for location in pocket_locations] == [0, 1, 2]


def test_generated_world_and_objective_progress_survive_reload() -> None:
    simulation = create_circus_simulation(seed=10)
    simulation.run(4)
    repository = InMemoryStateRepository()
    simulation.save(repository)
    restored = Simulation.load(repository, seed=10)
    before = next(iter(simulation.world.adventures.values()))
    after = next(iter(restored.world.adventures.values()))

    assert after.world_theme == before.world_theme
    assert after.generated_location_ids == before.generated_location_ids
    assert [objective.status for objective in after.objectives] == [objective.status for objective in before.objectives]
    assert all(location_id in restored.world.locations for location_id in after.generated_location_ids)


def test_browser_uses_free_steering_and_expanded_procedural_worlds() -> None:
    assert "NAV_ROUTES" not in WEB_SCRIPT
    assert "updateCharacterSteering" in WEB_SCRIPT
    assert "separationRadius" in WEB_SCRIPT
    assert "portalUntil" in WEB_SCRIPT
    assert "pocket_world_number" in WEB_SCRIPT
    for location in ("circus_grounds", "rides_promenade", "digital_lake", "portal_gallery", "grand_theater", "void_overlook"):
        assert location in WEB_SCRIPT
