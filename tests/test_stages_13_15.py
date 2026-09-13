from __future__ import annotations

from pathlib import Path

from autonomous_ai_world.adventures import CIRCUS_ADVENTURES
from autonomous_ai_world.persistence import InMemoryStateRepository
from autonomous_ai_world.simulation import Simulation, create_circus_simulation


WEB_SCRIPT = (
    Path(__file__).parents[1] / "src" / "autonomous_ai_world" / "web" / "app.js"
).read_text(encoding="utf-8")


def test_stage_13_maps_emotion_to_face_and_body_targets() -> None:
    assert "eyeTarget" in WEB_SCRIPT
    assert "headTilt" in WEB_SCRIPT
    assert "browAngle" in WEB_SCRIPT
    assert "armPosture" in WEB_SCRIPT
    assert "gestureUntil" in WEB_SCRIPT


def test_stage_14_camera_director_scores_and_frames_events() -> None:
    assert "cameraDirector" in WEB_SCRIPT
    assert "directCamera" in WEB_SCRIPT
    assert "frameConversation" in WEB_SCRIPT
    assert "frameCharacter" in WEB_SCRIPT
    assert "frameLocation" in WEB_SCRIPT
    assert "cinematic-target" in WEB_SCRIPT


def test_stage_15_caine_builds_pacing_and_development_context() -> None:
    simulation = create_circus_simulation(seed=5)

    summary = simulation.director.summarize(simulation.world)

    assert simulation.director.advanced is True
    assert 0 <= simulation.director.pacing.tension <= 1
    assert simulation.director.pacing.focus_character_id in simulation.world.characters
    assert simulation.director.pacing.development_opportunity
    assert summary.pacing["arc_stage"] in {
        "setup", "rising_action", "revelation", "crisis", "recovery",
        "intermission", "renewal",
    }


def test_stage_15_has_multiple_adventure_arcs_and_reserved_world_expansion() -> None:
    simulation = create_circus_simulation(seed=6)

    assert len(CIRCUS_ADVENTURES) >= 3
    assert {template.hidden_location_id for template in CIRCUS_ADVENTURES} <= set(
        simulation.world.locations
    )
    assert "mirror_maze" in simulation.world.locations
    assert simulation.world.locations["mirror_maze"].exits == set()


def test_advanced_director_state_survives_save_and_load() -> None:
    simulation = create_circus_simulation(seed=7)
    simulation.director.summarize(simulation.world)
    simulation.director.pacing.major_events = 2
    simulation.director.pacing.world_expansions = 1
    repository = InMemoryStateRepository()
    simulation.save(repository)

    restored = Simulation.load(repository, seed=7)

    assert restored.director.advanced is True
    assert restored.director.pacing.major_events == 2
    assert restored.director.pacing.world_expansions == 1
    assert restored.director.pacing.focus_character_id in restored.world.characters
    assert len(restored.adventures.templates) == len(CIRCUS_ADVENTURES)
