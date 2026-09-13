"""Environment-based runtime configuration with no embedded credentials."""

from __future__ import annotations

import os
from dataclasses import dataclass

from autonomous_ai_world.ai import AIProvider, AIProviderError, MockAIProvider, UnavailableRealAIProvider


@dataclass(frozen=True, slots=True)
class Settings:
    ai_provider: str = "mock"
    ai_model: str = "mock-v1"
    ai_api_key: str | None = None
    ai_timeout_seconds: float = 2.0

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            ai_provider=os.getenv("AI_PROVIDER", "mock").strip().lower(),
            ai_model=os.getenv("AI_MODEL", "mock-v1").strip(),
            ai_api_key=os.getenv("AI_API_KEY"),
            ai_timeout_seconds=float(os.getenv("AI_TIMEOUT_SECONDS", "2.0")),
        )

    def create_provider(self) -> AIProvider:
        if self.ai_provider == "mock":
            return MockAIProvider()
        return UnavailableRealAIProvider(
            self.ai_provider, self.ai_model, self.ai_api_key
        )

    def validate_runtime(self) -> None:
        if self.ai_provider == "mock":
            return
        if not self.ai_api_key:
            raise AIProviderError(
                f"AI_API_KEY is required when AI_PROVIDER={self.ai_provider}"
            )
        raise AIProviderError(
            f"real provider '{self.ai_provider}' is not implemented; use AI_PROVIDER=mock"
        )
