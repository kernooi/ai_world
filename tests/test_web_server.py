from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from autonomous_ai_world.persistence import JsonStateRepository
from autonomous_ai_world.simulation import create_default_simulation
from autonomous_ai_world.web_server import WebRuntimeConfig, create_app


def make_app(tmp_path):
    return create_app(
        WebRuntimeConfig(
            seed=7,
            tick_seconds=60,
            state_path=tmp_path / "world.json",
            fresh=True,
            auto_run=False,
        )
    )


def test_health_snapshot_and_static_client(tmp_path) -> None:
    app = make_app(tmp_path)

    with TestClient(app) as client:
        health = client.get("/api/health")
        snapshot = client.get("/api/snapshot")
        page = client.get("/")
        script = client.get("/app.js")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert snapshot.status_code == 200
    assert {character["name"] for character in snapshot.json()["characters"]} == {
        "Pomni", "Ragatha", "Jax", "Gangle", "Kinger", "Zooble"
    }
    assert snapshot.json()["director"]["name"] == "Caine"
    assert page.status_code == 200
    assert "The Autonomous Digital Circus" in page.text
    assert script.status_code == 200
    assert "new WebSocket" in script.text


def test_websocket_starts_with_full_state_and_allows_only_observer_controls(tmp_path) -> None:
    app = make_app(tmp_path)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as socket:
            snapshot = socket.receive_json()
            controls = socket.receive_json()
            socket.send_json({"type": "character_action", "actor_id": "alice", "action": "move"})
            rejected = socket.receive_json()
            socket.send_json({"type": "observer_control", "control": "paused", "value": True})
            paused = socket.receive_json()
            socket.send_json({"type": "observer_control", "control": "speed", "value": 3})
            invalid_speed = socket.receive_json()

    assert snapshot["type"] == "snapshot"
    assert snapshot["state"]["tick"] == 0
    assert controls == {"type": "control_state", "paused": False, "speed": 1.0}
    assert rejected == {"type": "error", "message": "The browser is observer-only."}
    assert paused["paused"] is True
    assert invalid_speed["type"] == "error"
    assert app.state.runner.simulation.world.tick == 0


def test_runner_advances_broadcast_payload_and_autosaves(tmp_path) -> None:
    app = make_app(tmp_path)
    runner = app.state.runner

    message = asyncio.run(runner.advance_once())

    assert message["type"] == "tick"
    assert message["state"]["tick"] == 1
    assert message["events"]
    assert (tmp_path / "world.json").exists()


def test_browser_replaces_a_pre_circus_save_with_the_new_scenario(tmp_path) -> None:
    path = tmp_path / "old-world.json"
    create_default_simulation(seed=2).save(JsonStateRepository(path))

    app = create_app(
        WebRuntimeConfig(seed=7, state_path=path, fresh=False, auto_run=False)
    )

    assert set(app.state.runner.simulation.world.characters) == {
        "pomni", "ragatha", "jax", "gangle", "kinger", "zooble"
    }
    assert (tmp_path / "old-world.pre-circus.json").exists()
