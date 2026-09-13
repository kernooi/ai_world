from __future__ import annotations

import asyncio
import random

from autonomous_ai_world.agents import AgentTendencies, CharacterAgent
from autonomous_ai_world.ai import MockAIProvider
from autonomous_ai_world.memory import MemoryStore
from autonomous_ai_world.models import (
    ActionKind,
    Character,
    Event,
    EventKind,
    Goal,
    Perception,
    Personality,
    Relationship,
)


def perception(**changes: object) -> Perception:
    values = {
        "tick": 1,
        "location_id": "square",
        "location_name": "Square",
        "description": "A square.",
        "exits": ("forest",),
        "nearby_characters": ("friend",),
        "features": {"statue": "An unfamiliar statue."},
        "energy": 8,
        "recent_events": (),
        "nearby_energy": {"friend": 8},
    }
    values.update(changes)
    return Perception(**values)  # type: ignore[arg-type]


def decide(character: Character, view: Perception, memory: MemoryStore, seed: int = 1):
    agent = CharacterAgent(
        character.id,
        AgentTendencies(
            curiosity=character.personality.curiosity,
            sociability=character.personality.sociability,
        ),
        random.Random(seed),
        provider=MockAIProvider(),
    )
    return asyncio.run(agent.decide_async(view, character, memory))


def test_different_personalities_choose_differently_in_same_situation() -> None:
    curious = Character(
        "curious", "Curious", "square",
        personality=Personality(curiosity=1.0, sociability=0.0, impulsiveness=0.0),
        relationships={"friend": Relationship()},
    )
    social = Character(
        "social", "Social", "square",
        personality=Personality(curiosity=0.0, sociability=1.0, impulsiveness=0.0),
        relationships={"friend": Relationship()},
    )

    curious_choice = decide(curious, perception(), MemoryStore("curious"))
    social_choice = decide(social, perception(), MemoryStore("social"))

    assert curious_choice.action.kind is ActionKind.INSPECT
    assert social_choice.action.kind is ActionKind.TALK


def test_personal_goal_changes_action_priority_and_choice() -> None:
    collector = Character(
        "collector", "Collector", "river",
        personality=Personality(curiosity=0.5, sociability=0, impulsiveness=0),
        goals=[Goal("wealth", "Find resources", 1.0, ("resource",))],
    )
    explorer = Character(
        "explorer", "Explorer", "river",
        personality=Personality(curiosity=0.5, sociability=0, impulsiveness=0),
        goals=[Goal("explore", "Explore", 1.0, ("explore",))],
    )
    view = perception(
        location_id="river", location_name="River", nearby_characters=(),
        nearby_energy={}, features={}, visible_objects={"gem": "A bright gem."},
    )

    assert decide(collector, view, MemoryStore("collector")).action.kind is ActionKind.PICK_UP
    assert decide(explorer, view, MemoryStore("explorer")).action.kind in {
        ActionKind.EXPLORE,
        ActionKind.MOVE,
    }


def test_important_danger_memory_changes_later_decision() -> None:
    character = Character(
        "wanderer", "Wanderer", "square",
        personality=Personality(
            curiosity=1.0, risk_tolerance=0.7, sociability=0, impulsiveness=0
        ),
        goals=[Goal("explore", "Explore", 1.0, ("explore",))],
    )
    view = perception(nearby_characters=(), nearby_energy={}, features={})
    without_memory = decide(character, view, MemoryStore("wanderer"), seed=3)
    store = MemoryStore("wanderer")
    store.remember_event(
        Event(
            1, 0, EventKind.SITUATION_CREATED, None, "forest",
            "A dangerous storm struck the forest.", {}, 0.9,
        )
    )
    with_memory = decide(character, view, store, seed=3)

    assert without_memory.action.kind is ActionKind.MOVE
    assert with_memory.action.kind is ActionKind.EXPLORE


def test_relationship_state_influences_social_choice() -> None:
    friendly = Character(
        "owner", "Owner", "square",
        personality=Personality(curiosity=0, sociability=0.2, impulsiveness=0),
        relationships={"friend": Relationship(trust=0.9, friendship=0.9)},
    )
    hostile = Character(
        "owner", "Owner", "square",
        personality=Personality(curiosity=0, sociability=0.2, impulsiveness=0),
        relationships={"friend": Relationship(trust=0, friendship=0, anger=1)},
    )
    view = perception(features={}, exits=())

    friendly_choice = decide(friendly, view, MemoryStore("owner"))
    hostile_choice = decide(hostile, view, MemoryStore("owner"))

    assert friendly_choice.action.kind is ActionKind.TALK
    assert hostile_choice.action.kind is not ActionKind.TALK
