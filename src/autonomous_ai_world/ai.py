"""Replaceable asynchronous AI provider interface and deterministic mock."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Mapping
from typing import Any


class AIProviderError(RuntimeError):
    pass


class AIProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def generate_structured(
        self, task: str, context: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        raise NotImplementedError


class MockAIProvider(AIProvider):
    """Deterministic offline provider used by development and all tests."""

    def __init__(
        self,
        responses: list[Mapping[str, Any] | Exception] | None = None,
        delay: float = 0.0,
    ) -> None:
        self.responses = deque(responses or [])
        self.delay = delay
        self.calls: list[dict[str, Any]] = []

    async def generate(self, prompt: str) -> str:
        if self.delay:
            await asyncio.sleep(self.delay)
        self.calls.append({"task": "generate", "prompt": prompt})
        return "Mock response"

    async def generate_structured(
        self, task: str, context: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        if self.delay:
            await asyncio.sleep(self.delay)
        self.calls.append({"task": task, "context": dict(context)})
        if self.responses:
            response = self.responses.popleft()
            if isinstance(response, Exception):
                raise response
            return response
        candidates = context.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise AIProviderError("mock provider requires decision candidates")
        return max(candidates, key=lambda item: float(item.get("score", 0.0)))


class UnavailableRealAIProvider(AIProvider):
    """Clear placeholder until a real provider adapter is intentionally added."""

    def __init__(self, provider_name: str, model: str, api_key: str | None) -> None:
        self.provider_name = provider_name
        self.model = model
        self.api_key = api_key

    def _error(self) -> AIProviderError:
        if not self.api_key:
            return AIProviderError(
                f"AI_API_KEY is required when AI_PROVIDER={self.provider_name}"
            )
        return AIProviderError(
            f"real provider '{self.provider_name}' is not implemented; use AI_PROVIDER=mock"
        )

    async def generate(self, prompt: str) -> str:
        raise self._error()

    async def generate_structured(
        self, task: str, context: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        raise self._error()

