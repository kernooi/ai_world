"""Emergent episode summaries and persistent world chronicle for Stage 20."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from autonomous_ai_world.models import Event, EventKind


@dataclass(slots=True)
class Episode:
    id: str
    number: int
    title: str
    premise: str
    start_tick: int
    start_day: int
    adventure_id: str | None = None
    status: str = "active"
    end_tick: int | None = None
    important_character_ids: list[str] = field(default_factory=list)
    major_event_sequences: list[int] = field(default_factory=list)
    memorable_moments: list[dict[str, Any]] = field(default_factory=list)
    key_outcomes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "premise": self.premise,
            "start_tick": self.start_tick,
            "start_day": self.start_day,
            "adventure_id": self.adventure_id,
            "status": self.status,
            "end_tick": self.end_tick,
            "important_character_ids": list(self.important_character_ids),
            "major_event_sequences": list(self.major_event_sequences),
            "memorable_moments": [dict(item) for item in self.memorable_moments],
            "key_outcomes": list(self.key_outcomes),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Episode:
        known = {name for name in cls.__dataclass_fields__}
        return cls(**{key: value for key, value in raw.items() if key in known})


@dataclass(slots=True)
class EpisodeManager:
    """Builds episodes from facts rather than imposing a fixed script."""

    episodes: list[Episode] = field(default_factory=list)
    major_consequences: list[dict[str, Any]] = field(default_factory=list)
    current_day: int = 1

    @property
    def active(self) -> Episode | None:
        return next((item for item in reversed(self.episodes) if item.status == "active"), None)

    def maintain(self, day: int, tick: int) -> None:
        active = self.active
        if active and active.start_day < day and active.adventure_id is None:
            self._close(active, tick, "The circus day ended with its consequences still unfolding.")
        self.current_day = day

    def observe(self, event: Event) -> None:
        if event.kind is EventKind.TIME_ADVANCED:
            return
        active = self.active
        is_director_incident = event.actor_id is None and event.kind in {
            EventKind.ADVENTURE_STARTED,
            EventKind.SITUATION_CREATED,
            EventKind.ENVIRONMENT_CHANGED,
            EventKind.WEATHER_CHANGED,
        }
        if active is None and is_director_incident:
            self._start(event)
            active = self.active
        if active is None:
            return

        target_id = event.data.get("target_id")
        social_target = target_id if (
            isinstance(target_id, str)
            and event.kind in {EventKind.SPOKE, EventKind.LIED, EventKind.HELPED}
        ) else None
        for character_id in (event.actor_id, social_target):
            if character_id and character_id not in active.important_character_ids:
                active.important_character_ids.append(character_id)
        if event.importance >= 0.82 or event.kind in {
            EventKind.OBJECT_DISCOVERED,
            EventKind.ADVENTURE_STARTED,
            EventKind.ADVENTURE_PROGRESSED,
            EventKind.ADVENTURE_RESOLVED,
            EventKind.ADVENTURE_EXPIRED,
            EventKind.ENVIRONMENT_CHANGED,
        }:
            if event.sequence not in active.major_event_sequences:
                active.major_event_sequences.append(event.sequence)
                active.major_event_sequences.sort()
        if event.importance >= 0.84 or event.kind in {
            EventKind.OBJECT_DISCOVERED,
            EventKind.ADVENTURE_STARTED,
            EventKind.ADVENTURE_PROGRESSED,
            EventKind.ADVENTURE_RESOLVED,
            EventKind.ADVENTURE_EXPIRED,
            EventKind.ENVIRONMENT_CHANGED,
        }:
            active.memorable_moments.append(
                {"sequence": event.sequence, "tick": event.tick, "summary": event.summary}
            )
            active.memorable_moments.sort(key=lambda item: int(item["sequence"]))
            active.memorable_moments[:] = active.memorable_moments[-8:]

        if event.kind in {EventKind.ADVENTURE_RESOLVED, EventKind.ADVENTURE_EXPIRED}:
            outcome = str(event.data.get("outcome", event.summary))
            self._close(active, event.tick, outcome)
            self._remember_consequence(event, outcome)
        elif event.kind is EventKind.ENVIRONMENT_CHANGED:
            consequence = str(event.data.get("title", event.summary))
            active.key_outcomes.append(consequence)
            self._remember_consequence(event, consequence)

    def _start(self, event: Event) -> None:
        number = len(self.episodes) + 1
        title = str(event.data.get("title", "An Unexpected Circus Day"))
        if event.kind is EventKind.ADVENTURE_STARTED:
            title = str(event.data.get("title", title))
        premise = str(event.data.get("premise", event.summary))
        self.episodes.append(
            Episode(
                id=f"episode-{number}",
                number=number,
                title=title,
                premise=premise,
                start_tick=event.tick,
                start_day=self.current_day,
                adventure_id=(
                    str(event.data["adventure_id"])
                    if event.kind is EventKind.ADVENTURE_STARTED
                    and "adventure_id" in event.data
                    else None
                ),
            )
        )

    @staticmethod
    def _close(episode: Episode, tick: int, outcome: str) -> None:
        episode.status = "complete"
        episode.end_tick = tick
        if outcome and outcome not in episode.key_outcomes:
            episode.key_outcomes.append(outcome)

    def _remember_consequence(self, event: Event, summary: str) -> None:
        if any(item["sequence"] == event.sequence for item in self.major_consequences):
            return
        self.major_consequences.append(
            {"sequence": event.sequence, "tick": event.tick, "kind": event.kind.value, "summary": summary}
        )
        self.major_consequences[:] = self.major_consequences[-100:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "episodes": [episode.to_dict() for episode in self.episodes],
            "major_consequences": [dict(item) for item in self.major_consequences],
            "current_day": self.current_day,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> EpisodeManager:
        if not raw:
            return cls()
        return cls(
            episodes=[Episode.from_dict(item) for item in raw.get("episodes", [])],
            major_consequences=[dict(item) for item in raw.get("major_consequences", [])],
            current_day=int(raw.get("current_day", 1)),
        )
