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
        protocol = client.get("/api/protocol")
        snapshot = client.get("/api/snapshot")
        page = client.get("/")
        script = client.get("/app.js")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["protocol_version"] == 1
    assert protocol.json()["observer_only"] is True
    assert protocol.json()["resume_buffer"] == 256
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
            socket.send_json({"type": "protocol_ack", "message_id": -1})
            bad_ack = socket.receive_json()
            socket.send_json({"type": "character_action", "actor_id": "alice", "action": "move"})
            rejected = socket.receive_json()
            socket.send_json({"type": "observer_control", "control": "paused", "value": True})
            paused = socket.receive_json()
            socket.send_json({"type": "observer_control", "control": "speed", "value": 3})
            invalid_speed = socket.receive_json()

    assert snapshot["type"] == "snapshot"
    assert snapshot["protocol_version"] == 1
    assert isinstance(snapshot["session_id"], str)
    assert isinstance(snapshot["message_id"], int)
    assert snapshot["state"]["tick"] == 0
    assert controls["type"] == "control_state"
    assert controls["paused"] is False
    assert controls["speed"] == 1.0
    assert bad_ack["message"] == "Invalid acknowledgement."
    assert rejected["type"] == "error"
    assert rejected["message"] == "The browser is observer-only."
    assert paused["paused"] is True
    assert invalid_speed["type"] == "error"
    assert app.state.runner.simulation.world.tick == 0


def test_runner_advances_broadcast_payload_and_autosaves(tmp_path) -> None:
    app = make_app(tmp_path)
    runner = app.state.runner

    message = asyncio.run(runner.advance_once())

    assert message["type"] == "tick"
    assert message["protocol_version"] == 1
    assert message["state"]["tick"] == 1
    assert message["events"]
    assert (tmp_path / "world.json").exists()


def test_tick_messages_are_buffered_for_same_session_resume(tmp_path) -> None:
    app = make_app(tmp_path)
    runner = app.state.runner

    first = asyncio.run(runner.advance_once())
    second = asyncio.run(runner.advance_once())
    replay = runner.connections.replay_since(first["session_id"], first["message_id"])

    assert replay == [second]
    assert runner.connections.replay_since("stale-session", 0) is None


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
