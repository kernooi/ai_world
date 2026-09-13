from __future__ import annotations

import random

from autonomous_ai_world.agents import AgentTendencies, CharacterAgent
from autonomous_ai_world.models import ActionKind
from autonomous_ai_world.simulation import create_default_simulation


def test_tired_agent_chooses_rest_from_perception() -> None:
    simulation = create_default_simulation(seed=4)
    simulation.world.characters["alice"].energy = 2
    agent = CharacterAgent(
        "alice",
        AgentTendencies(curiosity=1.0, sociability=1.0, rest_threshold=2),
        random.Random(1),
    )

    action = agent.decide(simulation.world.perceive("alice"))

    assert action.kind is ActionKind.REST


def test_curious_agent_inspects_a_perceived_feature() -> None:
    simulation = create_default_simulation(seed=4)
    agent = CharacterAgent(
        "alice",
        AgentTendencies(curiosity=1.0, sociability=0.0),
        random.Random(1),
    )

    action = agent.decide(simulation.world.perceive("alice"))

    assert action.kind is ActionKind.INSPECT
    assert action.target_id == "stone_well"


def test_agent_marks_inspected_features_and_then_varies_behavior() -> None:
    simulation = create_default_simulation(seed=4)
    agent = CharacterAgent(
        "alice",
        AgentTendencies(curiosity=1.0, sociability=0.0),
        random.Random(2),
    )
    perception = simulation.world.perceive("alice")

    first = agent.decide(perception)
    second = agent.decide(perception)

    assert first.kind is ActionKind.INSPECT
    assert second.kind in {ActionKind.MOVE, ActionKind.EXPLORE}

