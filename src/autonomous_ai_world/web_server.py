"""FastAPI host and autonomous simulation loop for the Stage 9 web world."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import shutil
import threading
import webbrowser
from collections.abc import AsyncIterator
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class WebRuntimeConfig:
    seed: int = 7
    tick_seconds: float = 2.5
    state_path: Path = Path(".runtime/world_state.json")
    fresh: bool = False
    auto_run: bool = True


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for connection in tuple(self.connections):
            try:
                await connection.send_json(message)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


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
        await self.connections.broadcast(message)
        return message

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
        await self.connections.broadcast(self.control_state)
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
    if not config.fresh and repository.path.exists():
        try:
            restored = Simulation.load(repository, seed=config.seed, settings=Settings.from_env())
            expected_cast = {"pomni", "ragatha", "jax", "gangle", "kinger", "zooble"}
            if set(restored.world.characters) == expected_cast:
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
        if config.auto_run:
            await runner.start()
        try:
            yield
        finally:
            await runner.stop()

    app = FastAPI(title="The Autonomous Digital Circus", version="0.9.0", lifespan=lifespan)
    app.state.runner = runner

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "tick": runner.simulation.world.tick,
            "clients": len(connections.connections),
            "paused": runner.paused,
            "speed": runner.speed,
        }

    @app.get("/api/snapshot")
    async def snapshot() -> JSONResponse:
        return JSONResponse(await runner.snapshot())

    @app.websocket("/ws")
    async def observer_socket(websocket: WebSocket) -> None:
        await connections.connect(websocket)
        try:
            await websocket.send_json({"type": "snapshot", "state": await runner.snapshot()})
            await websocket.send_json(runner.control_state)
            while True:
                message = await websocket.receive_json()
                if message.get("type") != "observer_control":
                    await websocket.send_json(
                        {"type": "error", "message": "The browser is observer-only."}
                    )
                    continue
                error = await runner.apply_control(message.get("control", ""), message.get("value"))
                if error:
                    await websocket.send_json({"type": "error", "message": error})
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
