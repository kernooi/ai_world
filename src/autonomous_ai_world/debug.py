"""Safe observability snapshots without exposing model chain-of-thought."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from autonomous_ai_world.simulation import Simulation


def debug_snapshot(simulation: Simulation) -> dict[str, Any]:
    world = simulation.world
    characters: dict[str, Any] = {}
    for character_id, character in world.characters.items():
        ordered_goals = sorted(character.goals, key=lambda goal: goal.priority, reverse=True)
        store = simulation.memory.store_for(character_id)
        agent = next(agent for agent in simulation.agents if agent.character_id == character_id)
        characters[character_id] = {
            "name": character.name,
            "location": character.location_id,
            "primary_goal": asdict(ordered_goals[0]) if ordered_goals else None,
            "secondary_goals": [asdict(goal) for goal in ordered_goals[1:]],
            "emotions": asdict(character.emotions),
            "physical_state": asdict(character.physical_state),
            "current_intention": (
                {
                    **asdict(character.current_intention),
                    "action_kind": character.current_intention.action_kind.value,
                }
                if character.current_intention
                else None
            ),
            "known_information": [fact.content for fact in character.knowledge.values()],
            "recent_memories": [memory.content for memory in store.recent[-5:]],
            "retrieved_memories": [memory.content for memory in agent.last_retrieved_memories],
            "relationships": {
                target: asdict(relationship)
                for target, relationship in character.relationships.items()
            },
            "last_action": (
                {
                    "kind": character.last_action.kind.value,
                    "target": character.last_action.target_id,
                }
                if character.last_action
                else None
            ),
            "last_action_result": (
                {
                    "accepted": character.last_action_result.accepted,
                    "summary": character.last_action_result.event.summary,
                }
                if character.last_action_result
                else None
            ),
            "provider_status": agent.last_provider_error or "ok",
        }
    summary = simulation.director.last_world_summary
    return {
        "world": {
            "tick": world.tick,
            "time": world.time.label,
            "weather": world.weather.value,
            "locations": {
                location.id: {
                    "exits": sorted(location.exits),
                    "objects": sorted(
                        obj.id for obj in world.objects.values() if obj.location_id == location.id
                    ),
                }
                for location in world.locations.values()
            },
            "recent_events": [event.summary for event in world.events.history[-10:]],
            "adventures": {
                adventure.id: {
                    "title": adventure.title,
                    "premise": adventure.premise,
                    "mystery": adventure.mystery,
                    "stakes": adventure.stakes,
                    "phase": adventure.phase.value,
                    "status": adventure.status.value,
                    "origin": adventure.origin_location_id,
                    "hidden_location": adventure.hidden_location_id,
                    "participants": sorted(adventure.participants),
                    "last_progress_tick": adventure.last_progress_tick,
                    "resolved_by": adventure.resolved_by,
                    "outcome": adventure.outcome,
                    "event_sequences": list(adventure.event_sequences),
                }
                for adventure in world.adventures.values()
            },
        },
        "characters": characters,
        "director": {
            "name": simulation.director.name,
            "advanced": simulation.director.advanced,
            "pacing": simulation.director.pacing.to_dict(),
            "status": simulation.director.status,
            "cooldown_remaining": simulation.director.cooldown_remaining,
            "last_error": simulation.director.last_error,
            "last_generated_event": (
                simulation.director.last_generated_event.summary
                if simulation.director.last_generated_event
                else None
            ),
            "world_summary": summary.to_dict() if summary else None,
            "adventure_status": (
                {
                    "active_id": (
                        simulation.adventures.active.id
                        if simulation.adventures and simulation.adventures.active
                        else None
                    ),
                    "last_error": simulation.adventures.last_error,
                }
                if simulation.adventures
                else None
            ),
        },
    }
