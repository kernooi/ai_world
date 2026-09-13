from __future__ import annotations

from autonomous_ai_world.models import Action, ActionKind
from autonomous_ai_world.simulation import create_default_simulation
from autonomous_ai_world.web_protocol import event_payload, world_snapshot


def test_snapshot_contains_renderable_public_state_without_private_state() -> None:
    simulation = create_default_simulation(seed=7)

    snapshot = world_snapshot(simulation)

    assert snapshot["tick"] == 0
    assert {item["id"] for item in snapshot["locations"]} >= {
        "village", "forest", "cave", "river", "observatory"
    }
    assert {item["id"] for item in snapshot["characters"]} == {"alice", "bob", "charlie"}
    assert {item["id"] for item in snapshot["objects"]} == {"river_berries"}
    alice = next(item for item in snapshot["characters"] if item["id"] == "alice")
    assert "goal" in alice and "intention" in alice and "physical" in alice
    assert "knowledge" not in alice
    assert "relationships" not in alice
    assert "memory" not in snapshot


def test_event_projection_is_json_ready_and_keeps_sequence() -> None:
    simulation = create_default_simulation(seed=2)
    result = simulation.world.execute(Action("alice", ActionKind.TALK, "bob", "Hello"))

    payload = event_payload(result.event)

    assert payload["sequence"] == result.event.sequence
    assert payload["kind"] == "spoke"
    assert payload["data"]["message"] == "Hello"


def test_snapshot_event_limit_is_applied() -> None:
    simulation = create_default_simulation(seed=3)
    simulation.run(3)

    snapshot = world_snapshot(simulation, event_limit=2)

    assert len(snapshot["events"]) == 2
    assert snapshot["events"][0]["sequence"] < snapshot["events"][1]["sequence"]
