"""Observer-safe JSON projections for the Stage 9 browser client."""

from __future__ import annotations

from enum import Enum
from typing import Any

from autonomous_ai_world.models import Event
from autonomous_ai_world.simulation import Simulation


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    return value


def event_payload(event: Event) -> dict[str, Any]:
    """Serialize a world fact without exposing model reasoning internals."""
    return {
        "sequence": event.sequence,
        "tick": event.tick,
        "kind": event.kind.value,
        "actor_id": event.actor_id,
        "location_id": event.location_id,
        "summary": event.summary,
        "data": _json_value(dict(event.data)),
        "importance": event.importance,
    }


def world_snapshot(simulation: Simulation, *, event_limit: int = 80) -> dict[str, Any]:
    """Build the public observer view; private memories and hidden objects stay server-side."""
    world = simulation.world
    characters = []
    for character in world.characters.values():
        emotions = {
            name: round(float(getattr(character.emotions, name)), 3)
            for name in character.emotions.__dataclass_fields__
        }
        dominant_emotion = max(emotions, key=emotions.get)
        goal = max(character.goals, key=lambda item: item.priority, default=None)
        intention = character.current_intention
        characters.append(
            {
                "id": character.id,
                "name": character.name,
                "location_id": character.location_id,
                "physical": {
                    "health": character.physical_state.health,
                    "energy": character.physical_state.energy,
                    "max_energy": character.physical_state.max_energy,
                    "hunger": character.physical_state.hunger,
                },
                "emotions": emotions,
                "dominant_emotion": dominant_emotion,
                "goal": goal.description if goal else None,
                "intention": (
                    {
                        "description": intention.description,
                        "action_kind": intention.action_kind.value,
                        "target_id": intention.target_id,
                        "reason": intention.reason,
                    }
                    if intention
                    else None
                ),
                "inventory": list(character.inventory),
            }
        )

    return {
        "tick": world.tick,
        "time": {
            "day": world.time.day,
            "minute": world.time.minute,
            "label": world.time.label,
            "is_night": world.time.is_night,
        },
        "weather": world.weather.value,
        "director": {
            "name": simulation.director.name,
            "status": simulation.director.status,
            "once_per_day": simulation.director.once_per_day,
            "last_event_day": simulation.director.last_intervention_day,
        },
        "locations": [
            {
                "id": location.id,
                "name": location.name,
                "description": location.description,
                "exits": sorted(location.exits),
                "features": [
                    {"id": feature_id, "description": description}
                    for feature_id, description in location.features.items()
                ],
                "danger": location.danger,
            }
            for location in world.locations.values()
        ],
        "characters": characters,
        "objects": [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "location_id": item.location_id,
                "held_by": item.held_by,
                "portable": item.portable,
                "tags": sorted(item.tags),
            }
            for item in world.objects.values()
            if not item.hidden
        ],
        "adventures": [
            {
                "id": adventure.id,
                "title": adventure.title,
                "premise": adventure.premise,
                "stakes": adventure.stakes,
                "origin_location_id": adventure.origin_location_id,
                "phase": adventure.phase.value,
                "status": adventure.status.value,
                "participants": sorted(adventure.participants),
                "resolved_by": adventure.resolved_by,
                "outcome": adventure.outcome,
            }
            for adventure in world.adventures.values()
        ],
        "events": [event_payload(event) for event in world.events.history[-event_limit:]],
    }
