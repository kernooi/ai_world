"""Data-driven Stage 8 adventure seeding and event-driven phase progression."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Any, Mapping

from autonomous_ai_world.ai import AIProvider
from autonomous_ai_world.models import (
    Adventure,
    AdventurePhase,
    AdventureStatus,
    Event,
    EventKind,
)
from autonomous_ai_world.world import World


@dataclass(frozen=True, slots=True)
class AdventureTemplate:
    id: str
    title: str
    premise: str
    mystery: str
    stakes: str
    hook_name: str
    hook_description: str
    clue_name: str
    clue_description: str
    hidden_location_id: str
    escalation_name: str
    escalation_description: str


DEFAULT_ADVENTURES = (
    AdventureTemplate(
        id="echo_below",
        title="The Echo Below",
        premise="A repeating signal seems to answer the residents' movements.",
        mystery="What is producing the signal, and why has it begun responding now?",
        stakes="The signal is growing stronger and may destabilize its hidden source.",
        hook_name="responsive_signal",
        hook_description=(
            "A soft sequence of tones repeats nearby, changing whenever someone moves."
        ),
        clue_name="a resonant compass shard",
        clue_description=(
            "The metal shard vibrates in time with the signal and points toward a sealed path."
        ),
        hidden_location_id="observatory",
        escalation_name="unstable_signal_core",
        escalation_description=(
            "A suspended ring of metal and light pulses faster as anyone approaches it."
        ),
    ),
)

CIRCUS_ADVENTURES = (
    AdventureTemplate(
        id="glitching_midway",
        title="The Glitching Midway",
        premise="Caine unveils a cheerful midway game whose prizes have begun rewriting the tent.",
        mystery="Which impossible prize is causing the glitch, and what does it want the cast to play?",
        stakes="If the game keeps spreading, every room may be folded into an endless obstacle course.",
        hook_name="laughing_scoreboard",
        hook_description=(
            "A neon scoreboard laughs, changes its own rules, and awards points for things nobody did."
        ),
        clue_name="a pixelated golden ticket",
        clue_description=(
            "The ticket flickers between destinations and points toward Caine's sealed adventure portal."
        ),
        hidden_location_id="adventure_portal",
        escalation_name="impossible_prize_wheel",
        escalation_description=(
            "A towering prize wheel spins through symbols that do not fit inside ordinary geometry."
        ),
    ),
)


class AdventureManager:
    """Advances premises only in response to authoritative character events."""

    def __init__(
        self,
        rng: random.Random,
        templates: tuple[AdventureTemplate, ...] = DEFAULT_ADVENTURES,
        *,
        max_idle_ticks: int = 120,
    ) -> None:
        if not templates:
            raise ValueError("at least one adventure template is required")
        self.rng = rng
        self.templates = templates
        self.max_idle_ticks = max_idle_ticks
        self.last_error: str | None = None
        self.last_start_event: Event | None = None
        self._world: World | None = None

    def bind(self, world: World) -> None:
        if self._world is world:
            return
        self._world = world
        world.events.subscribe(self.observe)

    @property
    def active(self) -> Adventure | None:
        if self._world is None:
            return None
        return next(
            (
                adventure
                for adventure in self._world.adventures.values()
                if adventure.status is AdventureStatus.ACTIVE
            ),
            None,
        )

    async def maybe_start(
        self,
        world: World,
        provider: AIProvider,
        world_summary: Mapping[str, object],
        timeout_seconds: float,
    ) -> Event | None:
        self.bind(world)
        if self.active is not None:
            return None
        used_templates = {
            template.id
            for template in self.templates
            if any(adventure.id.startswith(f"{template.id}_") for adventure in world.adventures.values())
        }
        available = [template for template in self.templates if template.id not in used_templates]
        if not available:
            return None
        occupied = sorted(
            {
                character.location_id
                for character in world.characters.values()
                if character.location_id != available[0].hidden_location_id
            }
        )
        candidates = [
            {
                "template_id": template.id,
                "origin_location_id": self.rng.choice(occupied),
                "title": template.title,
                "premise": template.premise,
                "score": self._score_template(template, world),
            }
            for template in available
        ]
        try:
            raw = await asyncio.wait_for(
                provider.generate_structured(
                    "adventure_premise",
                    {"world_summary": dict(world_summary), "candidates": candidates},
                ),
                timeout=timeout_seconds,
            )
            template_id, origin_id = self._parse_selection(raw, candidates)
            template = next(item for item in available if item.id == template_id)
            adventure = self._instantiate(template, origin_id, world)
            event = world.start_adventure(adventure)
            self.last_start_event = event
            self.last_error = None
            return event
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            return None

    def observe(self, event: Event) -> None:
        world = self._world
        adventure = self.active
        if world is None or adventure is None or not event.actor_id:
            return
        try:
            if (
                event.kind is EventKind.INSPECTED
                and event.data.get("target_id") == adventure.hook_feature_id
                and adventure.phase is AdventurePhase.HOOK
            ):
                world.advance_adventure(
                    adventure.id,
                    AdventurePhase.INVESTIGATION,
                    actor_id=event.actor_id,
                    cause_event_sequence=event.sequence,
                )
            elif (
                event.kind is EventKind.OBJECT_DISCOVERED
                and event.data.get("object_id") == adventure.clue_object_id
                and adventure.phase in {AdventurePhase.HOOK, AdventurePhase.INVESTIGATION}
            ):
                if adventure.phase is AdventurePhase.HOOK:
                    world.advance_adventure(
                        adventure.id,
                        AdventurePhase.INVESTIGATION,
                        actor_id=event.actor_id,
                        cause_event_sequence=event.sequence,
                    )
                world.advance_adventure(
                    adventure.id,
                    AdventurePhase.DISCOVERY,
                    actor_id=event.actor_id,
                    cause_event_sequence=event.sequence,
                )
            elif (
                event.kind is EventKind.MOVED
                and event.data.get("to") == adventure.hidden_location_id
                and adventure.phase is AdventurePhase.DISCOVERY
            ):
                world.advance_adventure(
                    adventure.id,
                    AdventurePhase.ESCALATION,
                    actor_id=event.actor_id,
                    cause_event_sequence=event.sequence,
                )
            elif (
                event.kind is EventKind.INSPECTED
                and event.data.get("target_id") == adventure.escalation_feature_id
                and adventure.phase is AdventurePhase.ESCALATION
            ):
                world.advance_adventure(
                    adventure.id,
                    AdventurePhase.RESOLUTION,
                    actor_id=event.actor_id,
                    cause_event_sequence=event.sequence,
                )
        except ValueError as exc:
            self.last_error = f"progression validation: {exc}"

    def maintain(self, world: World) -> Event | None:
        adventure = self.active
        if (
            adventure
            and world.tick - adventure.last_progress_tick >= self.max_idle_ticks
        ):
            return world.expire_adventure(
                adventure.id,
                "The unexplained signal faded after nobody advanced the investigation.",
            )
        return None

    @staticmethod
    def _score_template(template: AdventureTemplate, world: World) -> float:
        curiosity = sum(
            character.personality.curiosity for character in world.characters.values()
        ) / max(1, len(world.characters))
        discovery_goals = max(
            (
                goal.priority
                for character in world.characters.values()
                for goal in character.goals
                if "discover" in goal.tags or "explore" in goal.tags
            ),
            default=0.0,
        )
        return min(1.0, 0.35 + curiosity * 0.3 + discovery_goals * 0.35)

    @staticmethod
    def _parse_selection(
        raw: Mapping[str, Any], candidates: list[dict[str, Any]]
    ) -> tuple[str, str]:
        if not isinstance(raw, Mapping):
            raise ValueError("adventure selection must be an object")
        template_id = raw.get("template_id")
        origin_id = raw.get("origin_location_id")
        allowed = {
            (candidate["template_id"], candidate["origin_location_id"])
            for candidate in candidates
        }
        if (template_id, origin_id) not in allowed:
            raise ValueError("adventure selection was not an offered candidate")
        return str(template_id), str(origin_id)

    @staticmethod
    def _instantiate(
        template: AdventureTemplate, origin_id: str, world: World
    ) -> Adventure:
        number = len(world.adventures) + 1
        prefix = f"{template.id}_{number}"
        return Adventure(
            id=prefix,
            title=template.title,
            premise=template.premise,
            mystery=template.mystery,
            stakes=template.stakes,
            origin_location_id=origin_id,
            hidden_location_id=template.hidden_location_id,
            hook_feature_id=f"{prefix}_hook",
            hook_description=template.hook_description,
            clue_object_id=f"{prefix}_clue",
            clue_name=template.clue_name,
            clue_description=template.clue_description,
            escalation_feature_id=f"{prefix}_core",
            escalation_description=template.escalation_description,
        )
