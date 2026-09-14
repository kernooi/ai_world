from __future__ import annotations

from pathlib import Path

from autonomous_ai_world.models import Action, ActionKind
from autonomous_ai_world.persistence import InMemoryStateRepository, JsonStateRepository
from autonomous_ai_world.simulation import Simulation, create_circus_simulation
from autonomous_ai_world.web_protocol import world_snapshot


WEB_SCRIPT = (
    Path(__file__).parents[1] / "src" / "autonomous_ai_world" / "web" / "app.js"
).read_text(encoding="utf-8")


def test_stage_16_persists_complete_world_and_recovers_backup(tmp_path) -> None:
    simulation = create_circus_simulation(seed=16)
    simulation.run(5)
    repository = InMemoryStateRepository()
    simulation.save(repository)
    restored = Simulation.load(repository, seed=16)

    assert restored.to_dict()["version"] == 4
    assert restored.systems.to_dict() == simulation.systems.to_dict()
    assert restored.episodes.to_dict() == simulation.episodes.to_dict()
    assert restored.world.characters["pomni"].psychology == simulation.world.characters["pomni"].psychology

    path = tmp_path / "world.json"
    resilient = JsonStateRepository(path)
    resilient.save({"generation": 1})
    resilient.save({"generation": 2})
    path.write_text("{broken", encoding="utf-8")
    assert resilient.load() == {"generation": 1}


def test_stage_17_circus_systems_respond_to_authoritative_events() -> None:
    simulation = create_circus_simulation(seed=17)
    stability_before = simulation.systems.digital_stability
    simulation.step()

    assert simulation.systems.show_phase in {"morning_setup", "matinee", "intermission", "after_hours"}
    assert simulation.systems.digital_stability < stability_before
    assert simulation.systems.constructed_features
    assert 3 <= simulation.systems.gloink_population <= 11
    assert world_snapshot(simulation)["systems"]["faction_influence"]["cast"] > 0


def test_stage_18_psychology_evolves_but_secrets_remain_private() -> None:
    simulation = create_circus_simulation(seed=18)
    ragatha = simulation.world.characters["ragatha"]
    before = ragatha.psychology.habits["help"]
    simulation.world.characters["pomni"].energy = 2
    simulation.world.characters["ragatha"].location_id = "main_tent"
    simulation.world.execute(Action("ragatha", ActionKind.HELP, target_id="pomni"))

    assert ragatha.psychology.habits["help"] > before
    assert ragatha.psychology.reputation > 0.84
    public = next(item for item in world_snapshot(simulation)["characters"] if item["id"] == "ragatha")
    assert "secrets" not in public["psychology"]
    assert public["psychology"]["identity"]


def test_stage_19_production_presentation_contract() -> None:
    for capability in (
        "SpotLight", "syncGloinks", "burstConfetti", "glitchFlash",
        "startAudio", "playEventSound", "setHardwareScalingLevel", "visibilitychange",
    ):
        assert capability in WEB_SCRIPT


def test_stage_20_builds_and_completes_emergent_episode() -> None:
    simulation = create_circus_simulation(seed=20)
    for _ in range(120):
        simulation.step()
        if simulation.episodes.episodes and simulation.episodes.episodes[0].status == "complete":
            break

    first = simulation.episodes.episodes[0]
    assert first.title == "The Glitching Midway"
    assert first.status == "complete"
    assert first.major_event_sequences
    assert first.memorable_moments
    assert first.key_outcomes
    assert simulation.episodes.major_consequences
    assert world_snapshot(simulation)["episodes"][0]["id"] == first.id
