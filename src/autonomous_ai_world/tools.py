"""Structured action schemas shared by AI providers and the world validator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from autonomous_ai_world.models import Action, ActionKind, Decision


class StructuredOutputError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ActionSpec:
    kind: ActionKind
    description: str
    requires_target: bool = False
    requires_message: bool = False


ACTION_SPECS = {
    spec.kind: spec
    for spec in (
        ActionSpec(ActionKind.MOVE, "Move to an adjacent location", True),
        ActionSpec(ActionKind.TALK, "Speak truthfully to a nearby character", True, True),
        ActionSpec(ActionKind.INSPECT, "Inspect a perceived feature, object, or character", True),
        ActionSpec(ActionKind.REST, "Recover some energy"),
        ActionSpec(ActionKind.EXPLORE, "Explore the current location"),
        ActionSpec(ActionKind.SEARCH, "Search for hidden objects"),
        ActionSpec(ActionKind.PICK_UP, "Pick up a visible portable object", True),
        ActionSpec(ActionKind.DROP, "Drop an inventory item", True),
        ActionSpec(ActionKind.USE_ITEM, "Use an inventory item", True),
        ActionSpec(ActionKind.SLEEP, "Sleep to restore energy"),
        ActionSpec(ActionKind.HELP, "Help a nearby character", True),
        ActionSpec(ActionKind.LIE, "Tell a nearby character a dishonest claim", True, True),
    )
}


def parse_decision(payload: Mapping[str, Any], actor_id: str) -> Decision:
    """Turn untrusted provider output into a strictly validated decision."""

    try:
        intent = payload["intent"]
        raw_action = payload["action"]
        priority = float(payload["priority"])
        reason = payload["reason"]
    except (KeyError, TypeError, ValueError) as exc:
        raise StructuredOutputError("decision is missing required fields") from exc
    if not isinstance(intent, str) or not intent.strip():
        raise StructuredOutputError("intent must be a non-empty string")
    if not isinstance(reason, str) or not reason.strip():
        raise StructuredOutputError("reason must be a non-empty string")
    if not isinstance(raw_action, Mapping):
        raise StructuredOutputError("action must be an object")
    if not 0.0 <= priority <= 1.0:
        raise StructuredOutputError("priority must be between 0 and 1")
    try:
        kind = ActionKind(raw_action["type"])
    except (KeyError, TypeError, ValueError) as exc:
        raise StructuredOutputError("action type is unsupported") from exc
    target = raw_action.get("target")
    message = raw_action.get("message")
    if target is not None and not isinstance(target, str):
        raise StructuredOutputError("action target must be a string")
    if message is not None and not isinstance(message, str):
        raise StructuredOutputError("action message must be a string")
    spec = ACTION_SPECS[kind]
    if spec.requires_target and not target:
        raise StructuredOutputError(f"{kind.value} requires a target")
    if spec.requires_message and (not message or not message.strip()):
        raise StructuredOutputError(f"{kind.value} requires a message")
    return Decision(
        intent=intent.strip(),
        action=Action(actor_id, kind, target_id=target, message=message),
        priority=priority,
        reason=reason.strip(),
    )


def decision_payload(decision: Decision, score: float | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "intent": decision.intent,
        "action": {
            "type": decision.action.kind.value,
            "target": decision.action.target_id,
            "message": decision.action.message,
        },
        "priority": decision.priority,
        "reason": decision.reason,
    }
    if score is not None:
        result["score"] = score
    return result

