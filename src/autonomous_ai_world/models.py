"""Typed contracts for agents, tools, memories, and authoritative world state."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


def _unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class ActionKind(str, Enum):
    MOVE = "move"
    TALK = "talk"
    INSPECT = "inspect"
    REST = "rest"
    EXPLORE = "explore"
    SEARCH = "search"
    PICK_UP = "pick_up"
    DROP = "drop"
    USE_ITEM = "use_item"
    SLEEP = "sleep"
    HELP = "help"
    LIE = "lie"


class EventKind(str, Enum):
    MOVED = "moved"
    SPOKE = "spoke"
    INSPECTED = "inspected"
    RESTED = "rested"
    EXPLORED = "explored"
    SEARCHED = "searched"
    OBJECT_DISCOVERED = "object_discovered"
    ITEM_PICKED_UP = "item_picked_up"
    ITEM_DROPPED = "item_dropped"
    ITEM_USED = "item_used"
    SLEPT = "slept"
    HELPED = "helped"
    LIED = "lied"
    ACTION_REJECTED = "action_rejected"
    SITUATION_CREATED = "situation_created"
    WEATHER_CHANGED = "weather_changed"
    ENVIRONMENT_CHANGED = "environment_changed"
    TIME_ADVANCED = "time_advanced"
    ADVENTURE_STARTED = "adventure_started"
    ADVENTURE_PROGRESSED = "adventure_progressed"
    ADVENTURE_RESOLVED = "adventure_resolved"
    ADVENTURE_EXPIRED = "adventure_expired"


class MemoryKind(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"


class Weather(str, Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    STORM = "storm"
    FOG = "fog"


class DirectorEventKind(str, Enum):
    SITUATION = "situation"
    WEATHER = "weather"
    OBJECT = "object"
    OPEN_PATH = "open_path"


class AdventurePhase(str, Enum):
    HOOK = "hook"
    INVESTIGATION = "investigation"
    DISCOVERY = "discovery"
    ESCALATION = "escalation"
    RESOLUTION = "resolution"


class AdventureStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class Personality:
    curiosity: float = 0.5
    bravery: float = 0.5
    risk_tolerance: float = 0.5
    empathy: float = 0.5
    honesty: float = 0.5
    patience: float = 0.5
    sociability: float = 0.5
    independence: float = 0.5
    competitiveness: float = 0.5
    loyalty: float = 0.5
    impulsiveness: float = 0.5

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _unit(getattr(self, name)))


@dataclass(slots=True)
class EmotionalState:
    happiness: float = 0.5
    fear: float = 0.1
    anger: float = 0.0
    curiosity: float = 0.5
    excitement: float = 0.3
    anxiety: float = 0.1
    loneliness: float = 0.1

    def adjust(self, **changes: float) -> None:
        for name, delta in changes.items():
            if name not in self.__dataclass_fields__:
                raise ValueError(f"unknown emotion '{name}'")
            setattr(self, name, _unit(getattr(self, name) + delta))

    def settle(self, amount: float = 0.03) -> None:
        for name, baseline in {"fear": 0.1, "anger": 0.0, "anxiety": 0.1}.items():
            value = getattr(self, name)
            setattr(self, name, value + (baseline - value) * amount)


@dataclass(frozen=True, slots=True)
class Goal:
    id: str
    description: str
    priority: float
    tags: tuple[str, ...] = ()
    target_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "priority", _unit(self.priority))


@dataclass(slots=True)
class PhysicalState:
    health: int = 100
    energy: int = 8
    max_energy: int = 10
    hunger: int = 0


@dataclass(frozen=True, slots=True)
class KnowledgeFact:
    id: str
    content: str
    learned_tick: int
    source: str
    confidence: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", _unit(self.confidence))


@dataclass(slots=True)
class Relationship:
    trust: float = 0.5
    friendship: float = 0.5
    respect: float = 0.5
    suspicion: float = 0.0
    fear: float = 0.0
    anger: float = 0.0
    affection: float = 0.3
    loyalty: float = 0.3

    def adjust(self, **changes: float) -> None:
        for name, delta in changes.items():
            if name not in self.__dataclass_fields__:
                raise ValueError(f"unknown relationship dimension '{name}'")
            setattr(self, name, _unit(getattr(self, name) + delta))


@dataclass(frozen=True, slots=True)
class Intention:
    description: str
    action_kind: ActionKind
    target_id: str | None
    priority: float
    reason: str


@dataclass(frozen=True, slots=True)
class Action:
    """A structured request from an agent; it cannot mutate the world itself."""

    actor_id: str
    kind: ActionKind
    target_id: str | None = None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class Decision:
    intent: str
    action: Action
    priority: float
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "priority", _unit(self.priority))


@dataclass(frozen=True, slots=True)
class Event:
    sequence: int
    tick: int
    kind: EventKind
    actor_id: str | None
    location_id: str | None
    summary: str
    data: Mapping[str, Any] = field(default_factory=dict)
    importance: float = 0.3

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", MappingProxyType(dict(self.data)))
        object.__setattr__(self, "importance", _unit(self.importance))


@dataclass(frozen=True, slots=True)
class ActionResult:
    accepted: bool
    event: Event


@dataclass(slots=True)
class Location:
    id: str
    name: str
    description: str
    exits: set[str] = field(default_factory=set)
    features: dict[str, str] = field(default_factory=dict)
    danger: float = 0.0


@dataclass(slots=True)
class WorldObject:
    id: str
    name: str
    description: str
    location_id: str | None
    portable: bool = False
    hidden: bool = False
    discovered_by: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    uses_remaining: int | None = None
    held_by: str | None = None


@dataclass(slots=True)
class Adventure:
    id: str
    title: str
    premise: str
    mystery: str
    stakes: str
    origin_location_id: str
    hidden_location_id: str
    hook_feature_id: str
    hook_description: str
    clue_object_id: str
    clue_name: str
    clue_description: str
    escalation_feature_id: str
    escalation_description: str
    phase: AdventurePhase = AdventurePhase.HOOK
    status: AdventureStatus = AdventureStatus.ACTIVE
    created_tick: int = 0
    last_progress_tick: int = 0
    participants: set[str] = field(default_factory=set)
    event_sequences: list[int] = field(default_factory=list)
    resolved_by: str | None = None
    outcome: str | None = None


@dataclass(slots=True)
class Character:
    id: str
    name: str
    location_id: str
    personality: Personality = field(default_factory=Personality)
    values: tuple[str, ...] = ()
    goals: list[Goal] = field(default_factory=list)
    fears: tuple[str, ...] = ()
    preferences: tuple[str, ...] = ()
    emotions: EmotionalState = field(default_factory=EmotionalState)
    physical_state: PhysicalState = field(default_factory=PhysicalState)
    knowledge: dict[str, KnowledgeFact] = field(default_factory=dict)
    relationships: dict[str, Relationship] = field(default_factory=dict)
    current_intention: Intention | None = None
    inventory: list[str] = field(default_factory=list)
    last_action: Action | None = None
    last_action_result: ActionResult | None = None
    retrieved_memory_ids: list[str] = field(default_factory=list)

    @property
    def energy(self) -> int:
        return self.physical_state.energy

    @energy.setter
    def energy(self, value: int) -> None:
        self.physical_state.energy = value

    @property
    def max_energy(self) -> int:
        return self.physical_state.max_energy


@dataclass(slots=True)
class WorldTime:
    day: int = 1
    minute: int = 8 * 60

    @property
    def label(self) -> str:
        return f"Day {self.day} - {self.minute // 60:02d}:{self.minute % 60:02d}"

    @property
    def is_night(self) -> bool:
        hour = self.minute // 60
        return hour < 6 or hour >= 20

    def advance(self, minutes: int) -> None:
        total = self.minute + minutes
        self.day += total // (24 * 60)
        self.minute = total % (24 * 60)


@dataclass(frozen=True, slots=True)
class Perception:
    """The deliberately limited slice of state visible to one character."""

    tick: int
    location_id: str
    location_name: str
    description: str
    exits: tuple[str, ...]
    nearby_characters: tuple[str, ...]
    features: Mapping[str, str]
    energy: int
    recent_events: tuple[Event, ...]
    time_label: str = "Day 1 - 08:00"
    is_night: bool = False
    weather: Weather = Weather.CLEAR
    visible_objects: Mapping[str, str] = field(default_factory=dict)
    inventory: tuple[str, ...] = ()
    known_facts: tuple[KnowledgeFact, ...] = ()
    location_danger: float = 0.0
    nearby_energy: Mapping[str, int] = field(default_factory=dict)
    hunger: int = 0
    inventory_tags: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    inventory_uses: Mapping[str, int | None] = field(default_factory=dict)
    active_adventures: tuple[Mapping[str, str], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "features", MappingProxyType(dict(self.features)))
        object.__setattr__(self, "visible_objects", MappingProxyType(dict(self.visible_objects)))
        object.__setattr__(self, "nearby_energy", MappingProxyType(dict(self.nearby_energy)))
        object.__setattr__(self, "inventory_tags", MappingProxyType(dict(self.inventory_tags)))
        object.__setattr__(self, "inventory_uses", MappingProxyType(dict(self.inventory_uses)))
        object.__setattr__(
            self,
            "active_adventures",
            tuple(MappingProxyType(dict(item)) for item in self.active_adventures),
        )


@dataclass(frozen=True, slots=True)
class DirectorEventRequest:
    kind: DirectorEventKind
    title: str
    location_id: str | None = None
    description: str = ""
    object_id: str | None = None
    weather: Weather | None = None
    destination_id: str | None = None
