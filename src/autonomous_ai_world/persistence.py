"""Small persistence abstraction and atomic JSON file implementation."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class PersistenceError(RuntimeError):
    pass


class StateRepository(ABC):
    @abstractmethod
    def save(self, state: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def load(self) -> dict[str, Any]:
        raise NotImplementedError


class InMemoryStateRepository(StateRepository):
    def __init__(self) -> None:
        self.state: dict[str, Any] | None = None

    def save(self, state: dict[str, Any]) -> None:
        self.state = json.loads(json.dumps(state))

    def load(self) -> dict[str, Any]:
        if self.state is None:
            raise PersistenceError("no saved state exists")
        return json.loads(json.dumps(self.state))


class JsonStateRepository(StateRepository):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        self.backup_path = self.path.with_suffix(f"{self.path.suffix}.backup")

    def save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path.parent, delete=False
            ) as handle:
                json.dump(state, handle, indent=2, sort_keys=True)
                temp_path = Path(handle.name)
            # Keep a last-known-good generation before the atomic replacement.
            if self.path.exists():
                shutil.copy2(self.path, self.backup_path)
            os.replace(temp_path, self.path)
        except (OSError, TypeError, ValueError) as exc:
            if temp_path and temp_path.exists():
                temp_path.unlink()
            raise PersistenceError(f"could not save state to {self.path}") from exc

    def load(self) -> dict[str, Any]:
        result: Any = None
        primary_error: Exception | None = None
        try:
            with self.path.open(encoding="utf-8") as handle:
                result = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            primary_error = exc
            try:
                with self.backup_path.open(encoding="utf-8") as handle:
                    result = json.load(handle)
            except (OSError, json.JSONDecodeError) as backup_exc:
                raise PersistenceError(f"could not load state from {self.path} or its backup") from backup_exc
        if not isinstance(result, dict):
            suffix = " (backup recovery attempted)" if primary_error else ""
            raise PersistenceError(f"saved state must be a JSON object{suffix}")
        return result
