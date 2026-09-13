"""Stage 7 Director: observes summaries and proposes validated circumstances."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping

from autonomous_ai_world.ai import AIProvider, MockAIProvider
from autonomous_ai_world.models import (
    DirectorEventKind,
    DirectorEventRequest,
    Event,
    EventKind,
    Weather,
)
from autonomous_ai_world.world import World

if TYPE_CHECKING:
    from autonomous_ai_world.adventures import AdventureManager


@dataclass(frozen=True, slots=True)
class SituationTemplate:
    slug: str
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class WorldSummary:
    time_label: str
    weather: str
    characters: tuple[dict[str, object], ...]
    recent_events: tuple[str, ...]
    active_adventures: tuple[dict[str, object], ...]
    relationship_tension: float
    activity_score: float

    def to_dict(self) -> dict[str, object]:
        return {
            "time": self.time_label,
            "weather": self.weather,
            "characters": list(self.characters),
            "recent_events": list(self.recent_events),
            "active_adventures": list(self.active_adventures),
            "relationship_tension": self.relationship_tension,
            "activity_score": self.activity_score,
        }


DEFAULT_SITUATIONS = (
    SituationTemplate(
        "silver_feather",
        "a silver feather drifts down without a bird in sight",
        "The feather is warm and vibrates faintly when held near the ground.",
    ),
    SituationTemplate(
        "distant_bell",
        "a bell rings from somewhere beneath the earth",
        "A low bell tone repeats at uneven intervals, though no bell is visible.",
    ),
    SituationTemplate(
        "blue_footprints",
        "a trail of luminous blue footprints appears",
        "The small blue prints cross the ground and stop abruptly at a wall.",
    ),
    SituationTemplate(
        "sealed_box",
        "a rain-worn sealed box is discovered",
        "The wooden box has three keyholes and a freshly carved spiral on its lid.",
    ),
)

CIRCUS_SITUATIONS = (
    SituationTemplate(
        "confetti_storm",
        "Caine announces a surprise indoor confetti storm",
        "Every piece of confetti whispers a different clue about a prize hidden in the tent.",
    ),
    SituationTemplate(
        "runaway_teacups",
        "Caine releases a parade of runaway wind-up teacups",
        "The teacups race between the rings and demand to be sorted by impossible colors.",
    ),
    SituationTemplate(
        "backward_band",
        "Caine's invisible big band begins playing backward",
        "The music makes nearby props float until someone discovers the correct rhythm.",
    ),
    SituationTemplate(
        "gloink_delivery",
        "Caine schedules a suspicious gloink delivery",
        "A wobbling parcel marked DEFINITELY SAFE arrives beneath the center spotlight.",
    ),
    SituationTemplate(
        "gravity_matinee",
        "Caine declares that gravity is optional for today's matinee",
        "Bright arrows appear on the floor while loose objects drift toward the trapeze.",
    ),
)


class DirectorAgent:
    """Creates world pressure on a cooldown without selecting character actions."""

    def __init__(
        self,
        rng: random.Random,
        interval: int = 3,
        situations: tuple[SituationTemplate, ...] = DEFAULT_SITUATIONS,
        provider: AIProvider | None = None,
        timeout_seconds: float = 2.0,
        adventure_manager: AdventureManager | None = None,
        name: str = "Director",
        once_per_day: bool = False,
    ) -> None:
        if interval < 1:
            raise ValueError("Director interval must be positive")
        if not situations:
            raise ValueError("Director requires at least one situation template")
        self.rng = rng
        self.interval = interval
        self.situations = situations
        self.provider = provider or MockAIProvider()
        self.timeout_seconds = timeout_seconds
        self.adventure_manager = adventure_manager
        self.name = name
        self.once_per_day = once_per_day
        self._created = 0
        self.last_intervention_tick: int | None = None
        self.last_intervention_day: int | None = None
        self.last_generated_event: Event | None = None
        self.last_world_summary: WorldSummary | None = None
        self.last_error: str | None = None
        self.status = "waiting"
        self.last_observed_tick = 0
        self.last_observed_day = 1

    @property
    def cooldown_remaining(self) -> int:
        if self.once_per_day:
            return 0 if self.last_intervention_day != self.last_observed_day else 1
        last = self.last_intervention_tick or 0
        return max(0, self.interval - (self.last_observed_tick - last))

    def summarize(self, world: World) -> WorldSummary:
        self.last_observed_tick = world.tick
        self.last_observed_day = world.time.day
        recent = world.events.history[-10:]
        actionable = [
            event
            for event in recent
            if event.kind
            not in {EventKind.RESTED, EventKind.SEARCHED, EventKind.ACTION_REJECTED}
        ]
        tensions = [
            relationship.anger + relationship.suspicion
            for character in world.characters.values()
            for relationship in character.relationships.values()
        ]
        summary = WorldSummary(
            time_label=world.time.label,
            weather=world.weather.value,
            characters=tuple(
                {
                    "id": character.id,
                    "location": character.location_id,
                    "primary_goal": (
                        max(character.goals, key=lambda goal: goal.priority).description
                        if character.goals
                        else None
                    ),
                    "intention": (
                        character.current_intention.description
                        if character.current_intention
                        else None
                    ),
                    "fear": round(character.emotions.fear, 3),
                    "energy": character.energy,
                }
                for character in world.characters.values()
            ),
            recent_events=tuple(event.summary for event in recent),
            active_adventures=tuple(
                {
                    "id": adventure.id,
                    "title": adventure.title,
                    "phase": adventure.phase.value,
                    "participants": sorted(adventure.participants),
                    "idle_ticks": world.tick - adventure.last_progress_tick,
                }
                for adventure in world.adventures.values()
                if adventure.status.value == "active"
            ),
            relationship_tension=(sum(tensions) / len(tensions) if tensions else 0.0),
            activity_score=min(1.0, len(actionable) / 8),
        )
        self.last_world_summary = summary
        return summary

    def _is_due(self, world: World) -> bool:
        if self.once_per_day:
            return world.tick > 0 and self.last_intervention_day != world.time.day
        last = self.last_intervention_tick or 0
        return world.tick > 0 and world.tick - last >= self.interval

    def update(self, world: World) -> Event | None:
        """Synchronous deterministic update retained for direct callers."""
        self.summarize(world)
        if not self._is_due(world):
            self.status = "cooldown"
            return None
        request = self._situation_request(world)
        return self._apply(world, request)

    async def update_async(self, world: World) -> Event | None:
        if self.adventure_manager:
            self.adventure_manager.bind(world)
            expired = self.adventure_manager.maintain(world)
            if expired:
                self.last_generated_event = expired
                self.last_intervention_tick = world.tick
                self.last_intervention_day = world.time.day
                self.status = "adventure_expired"
                return expired
        summary = self.summarize(world)
        if not self._is_due(world):
            self.status = "cooldown"
            return None
        if self.adventure_manager:
            adventure_event = await self.adventure_manager.maybe_start(
                world,
                self.provider,
                summary.to_dict(),
                self.timeout_seconds,
            )
            if adventure_event:
                self._created += 1
                self.last_intervention_tick = world.tick
                self.last_intervention_day = world.time.day
                self.last_generated_event = adventure_event
                self.status = "adventure_started"
                self.last_error = None
                return adventure_event
        candidates = self._candidate_payloads(world)
        self.status = "considering_intervention"
        try:
            raw = await asyncio.wait_for(
                self.provider.generate_structured(
                    "director_intervention",
                    {"world_summary": summary.to_dict(), "candidates": candidates},
                ),
                timeout=self.timeout_seconds,
            )
            request = self._parse_request(raw)
            allowed = {(item["kind"], item.get("location_id"), item.get("object_id")) for item in candidates}
            key = (request.kind.value, request.location_id, request.object_id)
            if key not in allowed:
                raise ValueError("Director selected an unavailable intervention")
            self.last_error = None
            return self._apply(world, request)
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.status = "provider_failed_no_intervention"
            return None

    def _candidate_payloads(self, world: World) -> list[dict[str, Any]]:
        situation = self._situation_request(world)
        candidates = [self._request_payload(situation, score=0.62)]
        occupied = sorted({character.location_id for character in world.characters.values()})
        location_id = self.rng.choice(occupied)
        object_id = f"odd_token_{self._created + 1}"
        candidates.append(
            self._request_payload(
                DirectorEventRequest(
                    DirectorEventKind.OBJECT,
                    "an unfamiliar brass token",
                    location_id=location_id,
                    description="A palm-sized brass token bears a symbol no resident recognizes.",
                    object_id=object_id,
                ),
                score=0.66 if self._created % 3 == 1 else 0.54,
            )
        )
        alternatives = [weather for weather in Weather if weather is not world.weather]
        new_weather = self.rng.choice(alternatives)
        candidates.append(
            self._request_payload(
                DirectorEventRequest(
                    DirectorEventKind.WEATHER,
                    f"the weather turns {new_weather.value}",
                    weather=new_weather,
                ),
                score=0.7 if world.tick % (self.interval * 2) == 0 else 0.5,
            )
        )
        return candidates

    def _situation_request(self, world: World) -> DirectorEventRequest:
        template = self.rng.choice(self.situations)
        occupied = sorted({character.location_id for character in world.characters.values()})
        location_id = self.rng.choice(occupied)
        next_number = self._created + 1
        return DirectorEventRequest(
            DirectorEventKind.SITUATION,
            template.title,
            location_id=location_id,
            description=template.description,
            object_id=f"{template.slug}_{next_number}",
        )

    @staticmethod
    def _request_payload(request: DirectorEventRequest, score: float) -> dict[str, Any]:
        return {
            "kind": request.kind.value,
            "title": request.title,
            "location_id": request.location_id,
            "description": request.description,
            "object_id": request.object_id,
            "weather": request.weather.value if request.weather else None,
            "destination_id": request.destination_id,
            "score": score,
        }

    @staticmethod
    def _parse_request(raw: Mapping[str, Any]) -> DirectorEventRequest:
        if not isinstance(raw, Mapping):
            raise ValueError("Director output must be an object")
        try:
            kind = DirectorEventKind(raw["kind"])
            title = raw["title"]
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("Director output has invalid required fields") from exc
        if not isinstance(title, str) or not title:
            raise ValueError("Director title must be non-empty")
        weather_raw = raw.get("weather")
        weather = Weather(weather_raw) if weather_raw else None
        return DirectorEventRequest(
            kind,
            title,
            location_id=raw.get("location_id"),
            description=str(raw.get("description", "")),
            object_id=raw.get("object_id"),
            weather=weather,
            destination_id=raw.get("destination_id"),
        )

    def _apply(self, world: World, request: DirectorEventRequest) -> Event | None:
        try:
            event = world.apply_director_event(request)
        except ValueError as exc:
            self.last_error = f"validation: {exc}"
            self.status = "intervention_rejected"
            return None
        self._created += 1
        self.last_intervention_tick = world.tick
        self.last_intervention_day = world.time.day
        self.last_generated_event = event
        self.status = "intervened"
        return event
