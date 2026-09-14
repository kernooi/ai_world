"""FastAPI host for the Stage 20 world and daily quest-world overhaul."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import shutil
import threading
import uuid
import webbrowser
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from autonomous_ai_world.config import Settings
from autonomous_ai_world.persistence import JsonStateRepository, PersistenceError
from autonomous_ai_world.simulation import Simulation, create_circus_simulation
from autonomous_ai_world.web_protocol import event_payload, world_snapshot

PROTOCOL_VERSION = 1


@dataclass(frozen=True, slots=True)
class WebRuntimeConfig:
    seed: int = 7
    tick_seconds: float = 2.5
    state_path: Path = Path(".runtime/world_state.json")
    fresh: bool = False
    auto_run: bool = True


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[WebSocket, int] = {}
        self.session_id = uuid.uuid4().hex
        self.message_id = 0
        self.replay: deque[dict[str, Any]] = deque(maxlen=256)
        self._heartbeat_task: asyncio.Task[None] | None = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[websocket] = 0

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.pop(websocket, None)

    def acknowledge(self, websocket: WebSocket, message_id: Any) -> bool:
        if not isinstance(message_id, int) or isinstance(message_id, bool) or message_id < 0:
            return False
        if websocket not in self.connections:
            return False
        self.connections[websocket] = max(self.connections[websocket], message_id)
        return True

    def _envelope(self, message: dict[str, Any]) -> dict[str, Any]:
        self.message_id += 1
        return {
            **message,
            "protocol_version": PROTOCOL_VERSION,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "server_time": datetime.now(UTC).isoformat(),
        }

    async def send(self, websocket: WebSocket, message: dict[str, Any]) -> dict[str, Any]:
        envelope = self._envelope(message)
        await websocket.send_json(envelope)
        return envelope

    async def broadcast(
        self, message: dict[str, Any], *, replayable: bool = True
    ) -> dict[str, Any]:
        envelope = self._envelope(message)
        if replayable:
            self.replay.append(envelope)
        stale: list[WebSocket] = []
        for connection in tuple(self.connections):
            try:
                await connection.send_json(envelope)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)
        return envelope

    def replay_since(self, session_id: str | None, message_id: int | None) -> list[dict[str, Any]] | None:
        if session_id != self.session_id or message_id is None or message_id < 0:
            return None
        if self.replay and message_id < self.replay[0]["message_id"] - 1:
            return None
        return [message for message in self.replay if message["message_id"] > message_id]

    async def start_heartbeat(self) -> None:
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat(), name="web-heartbeat")

    async def stop_heartbeat(self) -> None:
        task, self._heartbeat_task = self._heartbeat_task, None
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _heartbeat(self) -> None:
        while True:
            await asyncio.sleep(5)
            await self.broadcast({"type": "heartbeat"}, replayable=False)


class SimulationRunner:
    """Owns ticking, autosave, and the two observer playback controls."""

    def __init__(
        self,
        simulation: Simulation,
        repository: JsonStateRepository,
        connections: ConnectionManager,
        *,
        tick_seconds: float,
    ) -> None:
        self.simulation = simulation
        self.repository = repository
        self.connections = connections
        self.tick_seconds = max(0.25, tick_seconds)
        self.paused = False
        self.speed = 1.0
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    @property
    def control_state(self) -> dict[str, Any]:
        return {"type": "control_state", "paused": self.paused, "speed": self.speed}

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="autonomous-world-loop")

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        async with self._lock:
            self.simulation.save(self.repository)

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return world_snapshot(self.simulation)

    async def advance_once(self) -> dict[str, Any]:
        async with self._lock:
            events = await self.simulation.async_step()
            self.simulation.save(self.repository)
            snapshot = world_snapshot(self.simulation)
        message = {
            "type": "tick",
            "events": [event_payload(event) for event in events],
            "state": snapshot,
        }
        return await self.connections.broadcast(message)

    async def apply_control(self, control: str, value: Any) -> str | None:
        if control == "paused" and isinstance(value, bool):
            self.paused = value
        elif (
            control == "speed"
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value in {0.5, 1, 2, 4}
        ):
            self.speed = float(value)
        else:
            return "Only observer playback controls are allowed: paused or speed (0.5, 1, 2, 4)."
        await self.connections.broadcast(self.control_state, replayable=False)
        return None

    async def _run(self) -> None:
        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue
            await asyncio.sleep(self.tick_seconds / self.speed)
            if not self.paused:
                await self.advance_once()


def _load_simulation(config: WebRuntimeConfig) -> tuple[Simulation, JsonStateRepository]:
    repository = JsonStateRepository(config.state_path)
    if not config.fresh and (repository.path.exists() or repository.backup_path.exists()):
        try:
            restored = Simulation.load(repository, seed=config.seed, settings=Settings.from_env())
            expected_cast = {"pomni", "ragatha", "jax", "gangle", "kinger", "zooble"}
            if set(restored.world.characters) == expected_cast:
                current = create_circus_simulation(seed=config.seed, settings=Settings.from_env())
                for location_id, location in current.world.locations.items():
                    if location_id not in restored.world.locations:
                        restored.world.locations[location_id] = location
                for location_id in {
                    "main_tent", "center_stage", "circus_grounds", "rides_promenade",
                    "digital_lake", "portal_gallery", "grand_theater", "void_overlook",
                }:
                    restored.world.locations[location_id].exits.update(
                        current.world.locations[location_id].exits
                    )
                for character_id, character in restored.world.characters.items():
                    if not character.psychology.beliefs:
                        character.psychology = current.world.characters[character_id].psychology
                restored.director.advanced = True
                restored.director.situations = current.director.situations
                if restored.adventures and current.adventures:
                    restored.adventures.templates = current.adventures.templates
                return restored, repository
            backup = repository.path.with_name(
                f"{repository.path.stem}.pre-circus{repository.path.suffix}"
            )
            if not backup.exists():
                shutil.copy2(repository.path, backup)
        except PersistenceError:
            pass
    return create_circus_simulation(seed=config.seed, settings=Settings.from_env()), repository


def create_app(config: WebRuntimeConfig | None = None) -> FastAPI:
    config = config or WebRuntimeConfig()
    simulation, repository = _load_simulation(config)
    connections = ConnectionManager()
    runner = SimulationRunner(
        simulation, repository, connections, tick_seconds=config.tick_seconds
    )

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await connections.start_heartbeat()
        if config.auto_run:
            await runner.start()
        try:
            yield
        finally:
            await runner.stop()
            await connections.stop_heartbeat()

    app = FastAPI(title="The Autonomous Digital Circus", version="0.22.0", lifespan=lifespan)
    app.state.runner = runner

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "tick": runner.simulation.world.tick,
            "clients": len(connections.connections),
            "paused": runner.paused,
            "speed": runner.speed,
            "protocol_version": PROTOCOL_VERSION,
            "session_id": connections.session_id,
            "message_id": connections.message_id,
        }

    @app.get("/api/protocol")
    async def protocol() -> dict[str, Any]:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "session_id": connections.session_id,
            "resume_buffer": connections.replay.maxlen,
            "inbound_types": ["observer_control", "protocol_ack"],
            "observer_only": True,
        }

    @app.get("/api/snapshot")
    async def snapshot() -> JSONResponse:
        return JSONResponse(await runner.snapshot())

    @app.websocket("/ws")
    async def observer_socket(websocket: WebSocket) -> None:
        await connections.connect(websocket)
        try:
            session_id = websocket.query_params.get("session_id")
            try:
                since = int(websocket.query_params["since"]) if "since" in websocket.query_params else None
            except ValueError:
                since = None
            replay = connections.replay_since(session_id, since)
            if replay is None:
                await connections.send(
                    websocket, {"type": "snapshot", "state": await runner.snapshot()}
                )
            else:
                for replayed in replay:
                    await websocket.send_json(replayed)
                await connections.send(
                    websocket, {"type": "resumed", "replayed": len(replay)}
                )
            await connections.send(websocket, runner.control_state)
            while True:
                message = await websocket.receive_json()
                if message.get("type") == "protocol_ack":
                    if not connections.acknowledge(websocket, message.get("message_id")):
                        await connections.send(
                            websocket, {"type": "error", "message": "Invalid acknowledgement."}
                        )
                    continue
                if message.get("type") != "observer_control":
                    await connections.send(
                        websocket, {"type": "error", "message": "The browser is observer-only."}
                    )
                    continue
                error = await runner.apply_control(message.get("control", ""), message.get("value"))
                if error:
                    await connections.send(websocket, {"type": "error", "message": error})
        except WebSocketDisconnect:
            pass
        finally:
            connections.disconnect(websocket)

    web_root = Path(__file__).with_name("web")
    app.mount("/", StaticFiles(directory=web_root, html=True), name="web")
    return app


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the autonomous browser world")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--tick-seconds", type=float, default=2.5)
    parser.add_argument("--state", type=Path, default=Path(".runtime/world_state.json"))
    parser.add_argument("--fresh", action="store_true", help="Start a new world on this launch")
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    config = WebRuntimeConfig(
        seed=args.seed,
        tick_seconds=args.tick_seconds,
        state_path=args.state,
        fresh=args.fresh,
    )
    url = f"http://{args.host}:{args.port}"
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(create_app(config), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
