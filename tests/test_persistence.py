from __future__ import annotations

from autonomous_ai_world.models import Action, ActionKind
from autonomous_ai_world.persistence import InMemoryStateRepository, JsonStateRepository
from autonomous_ai_world.simulation import Simulation, create_default_simulation


def test_important_world_and_character_state_round_trip() -> None:
    simulation = create_default_simulation(seed=5)
    simulation.world.execute(Action("alice", ActionKind.HELP, target_id="bob"))
    simulation.run(4)
    repository = InMemoryStateRepository()

    simulation.save(repository)
    restored = Simulation.load(repository, seed=5)

    assert restored.world.tick == simulation.world.tick
    assert restored.world.time.label == simulation.world.time.label
    assert restored.world.weather == simulation.world.weather
    assert len(restored.world.events.history) == len(simulation.world.events.history)
    assert restored.world.characters["alice"].knowledge == simulation.world.characters["alice"].knowledge
    assert (
        restored.relationships.get("bob", "alice").trust
        == simulation.relationships.get("bob", "alice").trust
    )
    assert restored.memory.store_for("bob").all == simulation.memory.store_for("bob").all


def test_json_repository_supports_cross_session_continuation(tmp_path) -> None:
    path = tmp_path / "world.json"
    simulation = create_default_simulation(seed=6)
    simulation.run(3)
    simulation.save(JsonStateRepository(path))

    continued = Simulation.load(JsonStateRepository(path), seed=6)
    old_tick = continued.world.tick
    continued.step()

    assert old_tick == 3
    assert continued.world.tick == 4
    assert path.read_text(encoding="utf-8").startswith("{")

