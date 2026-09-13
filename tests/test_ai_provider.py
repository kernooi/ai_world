from __future__ import annotations

import asyncio

import pytest

from autonomous_ai_world.ai import AIProviderError, MockAIProvider
from autonomous_ai_world.config import Settings
from autonomous_ai_world.models import ActionKind
from autonomous_ai_world.simulation import create_default_simulation
from autonomous_ai_world.tools import StructuredOutputError, parse_decision


def test_mock_provider_deterministically_selects_highest_scored_candidate() -> None:
    provider = MockAIProvider()

    result = asyncio.run(
        provider.generate_structured(
            "character_decision",
            {"candidates": [{"score": 0.2, "intent": "a"}, {"score": 0.9, "intent": "b"}]},
        )
    )

    assert result["intent"] == "b"
    assert provider.calls[0]["task"] == "character_decision"


def test_structured_decision_rejects_unknown_tool() -> None:
    with pytest.raises(StructuredOutputError, match="unsupported"):
        parse_decision(
            {
                "intent": "teleport",
                "action": {"type": "teleport", "target": "cave"},
                "priority": 1,
                "reason": "fast",
            },
            "alice",
        )


def test_invalid_provider_output_falls_back_without_corrupting_world() -> None:
    simulation = create_default_simulation(seed=2)
    alice_agent = next(agent for agent in simulation.agents if agent.character_id == "alice")
    alice_agent.provider = MockAIProvider(responses=[{"invalid": True}])

    asyncio.run(simulation.async_step())

    assert alice_agent.last_provider_error is not None
    assert simulation.world.characters["alice"].last_action_result is not None
    assert simulation.world.characters["alice"].last_action_result.accepted


def test_timeout_uses_fallback_and_other_agents_still_act() -> None:
    simulation = create_default_simulation(seed=3)
    alice_agent = next(agent for agent in simulation.agents if agent.character_id == "alice")
    alice_agent.provider = MockAIProvider(delay=0.05)
    alice_agent.timeout_seconds = 0.001

    events = asyncio.run(simulation.async_step())

    assert alice_agent.last_provider_error is not None
    assert {event.actor_id for event in events if event.actor_id} == {"alice", "bob", "charlie"}


def test_non_mock_configuration_fails_clearly_without_credentials() -> None:
    settings = Settings(ai_provider="example", ai_api_key=None)

    with pytest.raises(AIProviderError, match="AI_API_KEY"):
        settings.validate_runtime()


def test_mock_decision_is_a_supported_action() -> None:
    simulation = create_default_simulation(seed=8)
    simulation.step()

    assert all(
        character.last_action and isinstance(character.last_action.kind, ActionKind)
        for character in simulation.world.characters.values()
    )

