"""Circus-specific environmental and social simulation for Stage 17."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from autonomous_ai_world.models import Event, EventKind


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(slots=True)
class CircusSystems:
    """Meaningful shared pressures which respond to authoritative world events.

    These are deliberately circus-specific instead of a generic economy: stability,
    audience energy, cast cohesion, props, food, Gloinks, and persistent set pieces all
    influence the visible world and provide an emergent record of each run.
    """

    show_phase: str = "morning_setup"
    digital_stability: float = 0.88
    audience_excitement: float = 0.34
    cast_cohesion: float = 0.58
    prop_condition: float = 0.92
    food_units: int = 99
    gloink_population: int = 6
    cycle: int = 0
    faction_influence: dict[str, float] = field(
        default_factory=lambda: {"cast": 0.5, "caine": 0.72, "gloinks": 0.18}
    )
    constructed_features: list[str] = field(default_factory=list)
    damaged_features: list[str] = field(default_factory=list)
    last_event_sequence: int = 0

    def advance(self, day: int, minute: int, tick: int) -> None:
        previous = self.show_phase
        hour = minute // 60
        if 6 <= hour < 11:
            self.show_phase = "morning_setup"
        elif 11 <= hour < 16:
            self.show_phase = "matinee"
        elif 16 <= hour < 20:
            self.show_phase = "intermission"
        else:
            self.show_phase = "after_hours"
        if previous != self.show_phase:
            self.cycle += 1

        # The circus repairs itself slowly, while unattended glitches accumulate.
        self.digital_stability = _unit(self.digital_stability + 0.0008 - self.gloink_population * 0.000025)
        self.prop_condition = _unit(self.prop_condition + 0.0006)
        baseline = {"morning_setup": 0.25, "matinee": 0.68, "intermission": 0.44, "after_hours": 0.2}[self.show_phase]
        self.audience_excitement = _unit(self.audience_excitement + (baseline - self.audience_excitement) * 0.008)
        self.cast_cohesion = _unit(self.cast_cohesion + (0.62 - self.cast_cohesion) * 0.008)

        # A deterministic population cycle makes saves/replays reproducible.
        population_wave = (tick // 24 + day * 3) % 9
        self.gloink_population = 3 + population_wave
        self.faction_influence["gloinks"] = _unit(0.08 + self.gloink_population / 35)
        self.faction_influence["cast"] = _unit(0.2 + self.cast_cohesion * 0.62)

    def observe(self, event: Event) -> None:
        # Event delivery may be re-entrant (an adventure transition can be emitted
        # while its causing event is still being delivered), so sequence order is
        # not assumed here. Each bus publication is observed exactly once.
        self.last_event_sequence = max(self.last_event_sequence, event.sequence)
        if event.kind is EventKind.HELPED:
            self.cast_cohesion = _unit(self.cast_cohesion + 0.0015)
            self.audience_excitement = _unit(self.audience_excitement + 0.0005)
        elif event.kind is EventKind.SPOKE:
            self.cast_cohesion = _unit(self.cast_cohesion + 0.001)
        elif event.kind is EventKind.LIED:
            self.cast_cohesion = _unit(self.cast_cohesion - 0.01)
        elif event.kind is EventKind.ADVENTURE_STARTED:
            self.audience_excitement = _unit(self.audience_excitement + 0.18)
            self.digital_stability = _unit(self.digital_stability - 0.06)
            feature = f"set:{event.data.get('adventure_id', event.sequence)}"
            if feature not in self.constructed_features:
                self.constructed_features.append(feature)
        elif event.kind is EventKind.ADVENTURE_PROGRESSED:
            self.audience_excitement = _unit(self.audience_excitement + 0.07)
            self.digital_stability = _unit(self.digital_stability - 0.015)
        elif event.kind is EventKind.ADVENTURE_RESOLVED:
            self.cast_cohesion = _unit(self.cast_cohesion + 0.07)
            self.digital_stability = _unit(self.digital_stability + 0.13)
            self.audience_excitement = _unit(self.audience_excitement + 0.12)
        elif event.kind is EventKind.ADVENTURE_EXPIRED:
            self.cast_cohesion = _unit(self.cast_cohesion - 0.04)
            self.audience_excitement = _unit(self.audience_excitement - 0.1)
        elif event.kind is EventKind.ENVIRONMENT_CHANGED:
            title = str(event.data.get("title", event.summary))
            lowered = title.lower()
            if "red alert" in lowered:
                self.digital_stability = _unit(self.digital_stability - 0.12)
                self.prop_condition = _unit(self.prop_condition - 0.16)
                if title not in self.damaged_features:
                    self.damaged_features.append(title)
            else:
                self.digital_stability = _unit(self.digital_stability + 0.025)
                if title not in self.constructed_features:
                    self.constructed_features.append(title)
        elif event.kind is EventKind.ITEM_USED and event.data.get("object_id") == "digital_cake":
            self.food_units = max(0, self.food_units - 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "show_phase": self.show_phase,
            "digital_stability": self.digital_stability,
            "audience_excitement": self.audience_excitement,
            "cast_cohesion": self.cast_cohesion,
            "prop_condition": self.prop_condition,
            "food_units": self.food_units,
            "gloink_population": self.gloink_population,
            "cycle": self.cycle,
            "faction_influence": dict(self.faction_influence),
            "constructed_features": list(self.constructed_features),
            "damaged_features": list(self.damaged_features),
            "last_event_sequence": self.last_event_sequence,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> CircusSystems:
        if not raw:
            return cls()
        known = {name for name in cls.__dataclass_fields__}
        return cls(**{key: value for key, value in raw.items() if key in known})
