"""Stage 7 Director: observes summaries and proposes validated circumstances."""

from __future__ import annotations

import asyncio
import random
from dataclasses import asdict, dataclass, field
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


@dataclass(slots=True)
class DirectorPacingState:
    tension: float = 0.2
    arc_stage: str = "setup"
    quiet_ticks: int = 0
    focus_character_id: str | None = None
    development_opportunity: str | None = None
    major_events: int = 0
    world_expansions: int = 0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def restore(self, data: Mapping[str, Any]) -> None:
        self.tension = max(0.0, min(1.0, float(data.get("tension", self.tension))))
        self.arc_stage = str(data.get("arc_stage", self.arc_stage))
        self.quiet_ticks = max(0, int(data.get("quiet_ticks", self.quiet_ticks)))
        focus = data.get("focus_character_id")
        self.focus_character_id = str(focus) if focus else None
        opportunity = data.get("development_opportunity")
        self.development_opportunity = str(opportunity) if opportunity else None
        self.major_events = max(0, int(data.get("major_events", self.major_events)))
        self.world_expansions = max(0, int(data.get("world_expansions", self.world_expansions)))


@dataclass(frozen=True, slots=True)
class WorldSummary:
    time_label: str
    weather: str
    characters: tuple[dict[str, object], ...]
    recent_events: tuple[str, ...]
    active_adventures: tuple[dict[str, object], ...]
    relationship_tension: float
    activity_score: float
    pacing: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "time": self.time_label,
            "weather": self.weather,
            "characters": list(self.characters),
            "recent_events": list(self.recent_events),
            "active_adventures": list(self.active_adventures),
            "relationship_tension": self.relationship_tension,
            "activity_score": self.activity_score,
            "pacing": dict(self.pacing),
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
        advanced: bool = False,
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
        self.advanced = advanced
        self.pacing = DirectorPacingState()
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
        relationship_tension = sum(tensions) / len(tensions) if tensions else 0.0
        activity_score = min(1.0, len(actionable) / 8)
        if self.advanced:
            self._update_pacing(world, relationship_tension, activity_score)
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
                    "world_theme": adventure.world_theme,
                    "quest_objective": adventure.quest_objective,
                    "phase": adventure.phase.value,
                    "objectives_complete": sum(
                        objective.status == "complete" for objective in adventure.objectives
                    ),
                    "objective_count": len(adventure.objectives),
                    "participants": sorted(adventure.participants),
                    "idle_ticks": world.tick - adventure.last_progress_tick,
                }
                for adventure in world.adventures.values()
                if adventure.status.value == "active"
            ),
            relationship_tension=relationship_tension,
            activity_score=activity_score,
            pacing=self.pacing.to_dict() if self.advanced else {},
        )
        self.last_world_summary = summary
        return summary

    def _update_pacing(
        self, world: World, relationship_tension: float, activity_score: float
    ) -> None:
        active = self.adventure_manager.active if self.adventure_manager else None
        phase_pressure = {
            "hook": 0.3, "investigation": 0.45, "discovery": 0.6,
            "escalation": 0.9, "resolution": 0.25,
        }.get(active.phase.value if active else "", 0.18)
        emotional_pressure = max(
            (
                character.emotions.fear * .55
                + character.emotions.anxiety * .35
                + character.emotions.anger * .1
                for character in world.characters.values()
            ),
            default=0.0,
        )
        observed = min(
            1.0,
            phase_pressure * .42
            + emotional_pressure * .3
            + relationship_tension * .18
            + activity_score * .1,
        )
        self.pacing.tension = round(self.pacing.tension * .62 + observed * .38, 3)
        self.pacing.quiet_ticks = self.pacing.quiet_ticks + 1 if activity_score < .25 else 0
        if active:
            self.pacing.arc_stage = {
                "hook": "setup", "investigation": "rising_action", "discovery": "revelation",
                "escalation": "crisis", "resolution": "recovery",
            }[active.phase.value]
        elif self.pacing.tension > .67:
            self.pacing.arc_stage = "crisis"
        elif self.pacing.quiet_ticks > 3:
            self.pacing.arc_stage = "renewal"
        else:
            self.pacing.arc_stage = "intermission"

        focus = max(
            world.characters.values(),
            key=lambda character: (
                character.emotions.anxiety
                + character.emotions.fear
                + character.emotions.loneliness
                + (1 - character.emotions.happiness) * .35
            ),
        )
        opportunities = {
            "pomni": "a courage choice with a truthful escape clue",
            "ragatha": "a chance to set a boundary while still helping someone",
            "jax": "a consequence that rewards responsibility over mockery",
            "gangle": "a creative problem only her perspective can solve",
            "kinger": "a quiet mystery that rewards a moment of clarity",
            "zooble": "a meaningful choice about identity and personal agency",
        }
        self.pacing.focus_character_id = focus.id
        self.pacing.development_opportunity = opportunities.get(
            focus.id, "a choice that tests a personal value"
        )

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
                self.status = "adventure_expired"
                # Closing yesterday's portal is housekeeping. It does not consume
                # today's promise of a new Caine-created quest world.
        summary = self.summarize(world)
        if self.adventure_manager and self.adventure_manager.active and self.adventure_manager.active.story:
            self.status = 'overseeing_adventure'
            return None
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
        if self.advanced and self.pacing.focus_character_id in world.characters:
            focus = world.characters[self.pacing.focus_character_id]
            candidates.append(
                self._request_payload(
                    DirectorEventRequest(
                        DirectorEventKind.SITUATION,
                        f"Caine spotlights {focus.name} for an unusually personal challenge",
                        location_id=focus.location_id,
                        description=str(self.pacing.development_opportunity),
                        object_id=f"development_{focus.id}_{world.time.day}",
                    ),
                    score=0.74 if self.pacing.tension < 0.68 else 0.59,
                )
            )
            if self.pacing.tension >= 0.58:
                candidates.append(
                    self._request_payload(
                        DirectorEventRequest(
                            DirectorEventKind.SITUATION,
                            "Caine triggers a tent-wide RED ALERT spectacular",
                            location_id=focus.location_id,
                            description=(
                                "The lights turn crimson, every exit moves, and a giant countdown asks "
                                "the cast to cooperate before the rings exchange places."
                            ),
                            object_id=f"major_red_alert_{world.time.day}",
                        ),
                        score=0.86,
                    )
                )
            expansion_id = "mirror_maze"
            if (
                self._created >= 2
                and expansion_id in world.locations
                and expansion_id not in world.locations[focus.location_id].exits
            ):
                candidates.append(
                    self._request_payload(
                        DirectorEventRequest(
                            DirectorEventKind.OPEN_PATH,
                            "a glittering corridor unfolds into the Infinite Mirror Maze.",
                            location_id=focus.location_id,
                            destination_id=expansion_id,
                        ),
                        score=0.82 if self._created >= 3 or self.pacing.quiet_ticks >= 2 else 0.69,
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
        if self.advanced:
            if request.kind is DirectorEventKind.OPEN_PATH:
                self.pacing.world_expansions += 1
            if request.object_id and request.object_id.startswith("major_"):
                self.pacing.major_events += 1
        self.last_intervention_tick = world.tick
        self.last_intervention_day = world.time.day
        self.last_generated_event = event
        self.status = "intervened"
        return event
