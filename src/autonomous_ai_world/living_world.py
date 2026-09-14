"""Authoritative spatial routines and activity affordances for the circus.

The semantic action model still owns consequences.  This layer gives those
actions a persistent physical performance: a destination, an activity spot,
and several visible steps instead of a random browser wander.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import math
from typing import TYPE_CHECKING, Any, Iterable

from autonomous_ai_world.models import Action, ActionKind

if TYPE_CHECKING:
    from autonomous_ai_world.world import World


@dataclass(frozen=True, slots=True)
class ActivitySpot:
    id: str
    location_id: str
    label: str
    kind: str
    x: float
    z: float
    capacity: int = 2
    verbs: tuple[str, ...] = ("observe",)


@dataclass(slots=True)
class RoutineStep:
    label: str
    activity: str
    x: float
    z: float
    spot_id: str | None = None
    duration: int = 1
    target_id: str | None = None


@dataclass(slots=True)
class SpatialCharacter:
    character_id: str
    location_id: str
    x: float
    z: float
    plan: list[RoutineStep] = field(default_factory=list)
    plan_index: int = 0
    phase: str = "idle"
    activity: str = "observing"
    dwell: int = -1
    revision: int = 0
    queued_action: Action | None = None


@dataclass(slots=True)
class DirectorPresence:
    """Caine's persistent physical presence, separate from character agency."""

    location_id: str = "center_stage"
    x: float = 0
    z: float = 0
    target_id: str | None = None
    last_target_id: str | None = None
    phase: str = "observing"
    next_check_tick: int = 4
    dwell: int = 0
    revision: int = 0
    check_count: int = 0
    visited_ids: list[str] = field(default_factory=list)


_SPOT_LAYOUTS: dict[str, tuple[tuple[str, str, str, float, float, int, tuple[str, ...]], ...]] = {
    "main_tent": (
        ("left_ring", "Left rehearsal ring", "performance", -13, 0, 3, ("rehearse", "perform")),
        ("right_ring", "Right rehearsal ring", "performance", 13, 0, 3, ("rehearse", "perform")),
        ("balloon_left", "Balloon cluster", "curiosity", -7, 6.8, 2, ("inspect", "tidy")),
        ("balloon_right", "Balloon cluster", "curiosity", 7, 6.8, 2, ("inspect", "tidy")),
        ("quiet_apron", "Quiet edge of the ring", "rest", 0, 8, 2, ("rest", "talk")),
    ),
    "center_stage": (
        ("caine_mark", "Caine's stage mark", "performance", 0, 7.2, 3, ("perform", "listen")),
        ("spotlight_left", "Left spotlight console", "machine", -8, 5.5, 1, ("inspect", "operate")),
        ("spotlight_right", "Right spotlight console", "machine", 8, 5.5, 1, ("inspect", "operate")),
    ),
    "bedroom_hall": (
        ("pomni_door", "Pomni's door", "personal", -7.5, 2, 1, ("visit", "inspect")),
        ("ragatha_door", "Ragatha's door", "personal", -4.5, 2, 1, ("visit", "talk")),
        ("jax_door", "Jax's door", "personal", -1.5, 2, 1, ("visit", "listen")),
        ("gangle_door", "Gangle's door", "personal", 1.5, 2, 1, ("visit", "draw")),
        ("kinger_door", "Kinger's door", "personal", 4.5, 2, 1, ("visit", "remember")),
        ("zooble_door", "Zooble's door", "personal", 7.5, 2, 1, ("visit", "repair")),
        ("false_exit", "Suspicious EXIT sign", "curiosity", 0, -3, 2, ("inspect", "search")),
    ),
    "dining_hall": (
        ("cake_service", "Regenerating cake", "food", 0, -3, 2, ("eat", "inspect")),
        ("west_seats", "West banquet seats", "social", -7.2, 1, 3, ("eat", "talk")),
        ("east_seats", "East banquet seats", "social", 7.2, 1, 3, ("eat", "talk")),
        ("tea_end", "Talking teapot", "food", 0, 5.2, 2, ("pour", "listen")),
    ),
    "backstage": (
        ("costume_rack", "Costume and mask rack", "creative", -6, -3, 2, ("draw", "repair", "inspect")),
        ("prop_workbench", "Prop workbench", "creative", 0, -3, 2, ("build", "repair")),
        ("ladder_station", "Impossible ladder", "danger", 6, -3, 1, ("climb", "inspect")),
        ("crate_maze", "Prop crate maze", "curiosity", -1, 8, 2, ("search", "hide")),
    ),
    "circus_grounds": (
        ("fountain_west", "Fountain promenade", "social", -5, 0, 3, ("talk", "watch")),
        ("fountain_east", "Fountain promenade", "social", 5, 0, 3, ("talk", "watch")),
        ("living_map", "Living map", "machine", 0, 6, 3, ("inspect", "plan")),
        ("garden_path", "Topiary garden", "rest", -7, -6, 2, ("walk", "rest")),
        ("midway_gate", "Midway gate", "travel", 7, -6, 3, ("meet", "plan")),
    ),
    "rides_promenade": (
        ("wheel_queue", "Ferris wheel queue", "ride", 0, -1, 4, ("queue", "ride")),
        ("west_booth", "Prize booth", "game", -5, -4, 2, ("play", "cheat")),
        ("east_booth", "Ticket booth", "game", 5, -4, 2, ("play", "talk")),
        ("midway_end", "Midway overlook", "rest", 0, -7, 3, ("watch", "talk")),
    ),
    "digital_lake": (
        ("pixel_dock", "Pixel boat dock", "ride", -10, -5, 2, ("launch", "repair")),
        ("toy_beach", "Toy beach", "rest", 9, -5, 3, ("rest", "search")),
        ("boathouse", "Self-assembling boathouse", "machine", 0, -6, 2, ("inspect", "build")),
    ),
    "portal_gallery": (
        ("portal_console", "Portal control rail", "machine", 0, -2, 3, ("inspect", "operate")),
        ("archive_left", "Adventure archive", "memory", -8, -1, 2, ("remember", "watch")),
        ("archive_right", "Adventure archive", "memory", 8, -1, 2, ("remember", "watch")),
    ),
    "grand_theater": (
        ("improv_mark", "Improvisation mark", "performance", 0, -3, 4, ("perform", "tell_story")),
        ("left_wing", "Left stage wing", "creative", -4, 0, 2, ("rehearse", "build")),
        ("right_wing", "Right stage wing", "creative", 4, 0, 2, ("rehearse", "watch")),
    ),
    "void_overlook": (
        ("boundary_glass", "Boundary glass", "danger", 0, 2, 2, ("inspect", "remember")),
        ("quiet_garden", "Quiet overlook garden", "rest", -7, -2, 2, ("rest", "talk")),
        ("unfinished_edge", "Unfinished geometry", "curiosity", 7, -2, 1, ("search", "inspect")),
    ),
}


class LivingWorld:
    """Persistent positions, destinations, activity spots, and routine steps."""

    def __init__(self, world: World, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self.spots: dict[str, ActivitySpot] = {}
        self.characters: dict[str, SpatialCharacter] = {}
        self.director = DirectorPresence()
        self._refresh_spots(world)
        for index, character in enumerate(world.characters.values()):
            angle = index * 2.39996
            self.characters[character.id] = SpatialCharacter(
                character.id, character.location_id,
                round(math.cos(angle) * 3.4, 3), round(math.sin(angle) * 3.4, 3),
            )

    @staticmethod
    def _number(text: str, low: float, high: float) -> float:
        raw = int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], "big") / 0xFFFFFFFF
        return round(low + raw * (high - low), 3)

    def _refresh_spots(self, world: World) -> None:
        for location in world.locations.values():
            if any(spot.location_id == location.id for spot in self.spots.values()):
                continue
            layout = _SPOT_LAYOUTS.get(location.id)
            if layout:
                for spot_id, label, kind, x, z, capacity, verbs in layout:
                    spot = ActivitySpot(f"{location.id}:{spot_id}", location.id, label, kind, x, z, capacity, verbs)
                    self.spots[spot.id] = spot
            else:
                # Adventure worlds and future Director-created rooms immediately
                # gain spatial affordances without special-case browser code.
                candidates = [("arrival", "Arrival point", "travel", -5.5, -4.5),
                              ("landmark", "Central landmark", "curiosity", 0, -5.5),
                              ("quest", "Quest approach", "adventure", 5.5, -4.5),
                              ("shelter", "Safe gathering spot", "rest", 0, 6.5)]
                for spot_id, label, kind, x, z in candidates:
                    spot = ActivitySpot(f"{location.id}:{spot_id}", location.id, label, kind, x, z, 3,
                                        ("inspect", "search") if kind != "rest" else ("rest", "talk"))
                    self.spots[spot.id] = spot

    def queue_actions(self, actions: Iterable[Action], world: World | None = None) -> None:
        for action in actions:
            if action.actor_id in self.characters:
                self.characters[action.actor_id].queued_action = action
        if world is not None:
            self.sync_locations(world)
            for state in self.characters.values():
                self._start_queued_plan(world, state)

    def sync_locations(self, world: World) -> None:
        """Immediately reconcile semantic travel before publishing a snapshot."""
        for character in world.characters.values():
            state = self.characters.get(character.id)
            if not state or state.location_id == character.location_id:
                continue
            state.location_id = character.location_id
            state.x = self._number(f"{character.id}:{character.location_id}:x", -4, 4)
            state.z = -6.5
            state.plan = []
            state.plan_index = 0
            state.phase = "arriving"
            state.activity = "arriving"
            state.revision += 1

    def is_busy(self, character_id: str) -> bool:
        state = self.characters.get(character_id)
        return bool(self.enabled and state and state.plan_index < len(state.plan))

    def _start_queued_plan(self, world: World, state: SpatialCharacter) -> bool:
        if state.plan_index < len(state.plan) or state.queued_action is None:
            return False
        state.plan = self._plan(world, state, state.queued_action)
        state.plan_index = 0
        state.dwell = -1
        state.revision += 1
        state.queued_action = None
        return True

    def advance(self, world: World, actions: Iterable[Action] = ()) -> None:
        if not self.enabled:
            return
        self._refresh_spots(world)
        self.queue_actions(actions, world)
        for character in world.characters.values():
            state = self.characters.setdefault(
                character.id, SpatialCharacter(character.id, character.location_id, 0, 0)
            )
            if state.plan_index >= len(state.plan):
                if not self._start_queued_plan(world, state):
                    state.plan = []
                    state.plan_index = 0
                    state.phase = "idle"
                    state.activity = "observing"
                    continue
            self._advance_character(world, state)
        self._advance_director(world)

    def _advance_director(self, world: World) -> None:
        """Let Caine visit cast members without assigning him a fixed route."""
        state = self.director
        if not self.characters:
            return
        if state.target_id is None:
            if world.tick < state.next_check_tick:
                state.phase = "observing"
                return
            candidates = [item for item in sorted(self.characters) if item not in state.visited_ids]
            if not candidates:
                state.visited_ids = []
                candidates = sorted(self.characters)
            if len(candidates) > 1 and state.last_target_id in candidates:
                candidates.remove(state.last_target_id)
            # Deterministic but non-cyclic selection keeps save/load stable while
            # avoiding a visible railroad patrol around the cast list.
            pick = int(self._number(f"caine:{world.time.day}:{world.tick}:{state.check_count}", 0, 10000))
            state.target_id = candidates[pick % len(candidates)]
            state.phase = "traveling"
            state.dwell = 2
            state.revision += 1

        target = self.characters.get(state.target_id)
        if target is None:
            state.target_id = None
            state.next_check_tick = world.tick + 4
            return
        if target.location_id != state.location_id:
            state.location_id = target.location_id
            # Caine portals into the room at a visible distance, then flies the
            # rest of the way instead of snapping directly onto the resident.
            state.x = round(target.x - 6, 3)
            state.z = round(target.z - 5, 3)
            state.revision += 1

        side = -1 if state.check_count % 2 else 1
        destination_x, destination_z = target.x + side * 2.6, target.z - 2.4
        dx, dz = destination_x - state.x, destination_z - state.z
        distance = math.hypot(dx, dz)
        already_checking = state.phase == "checking"
        if distance > .25:
            # Caine flies faster than the walking cast so a moving target cannot
            # accidentally turn a check-up into an endless chase.
            stride = min(5.6, distance)
            state.x = round(state.x + dx / distance * stride, 3)
            state.z = round(state.z + dz / distance * stride, 3)
            state.phase = "checking" if already_checking else "traveling"
            if already_checking:
                if state.dwell > 0:
                    state.dwell -= 1
                else:
                    self._finish_director_check(world, state)
            return
        state.x, state.z = round(destination_x, 3), round(destination_z, 3)
        state.phase = "checking"
        if state.dwell > 0:
            state.dwell -= 1
            return
        self._finish_director_check(world, state)

    @staticmethod
    def _finish_director_check(world: World, state: DirectorPresence) -> None:
        state.last_target_id = state.target_id
        if state.target_id and state.target_id not in state.visited_ids:
            state.visited_ids.append(state.target_id)
        state.target_id = None
        state.check_count += 1
        # Roughly 12.5-20 seconds at the default web tick rate.
        state.next_check_tick = world.tick + 4 + (state.check_count % 3)
        state.phase = "observing"
        state.revision += 1

    def _location_spots(self, location_id: str) -> list[ActivitySpot]:
        return [spot for spot in self.spots.values() if spot.location_id == location_id]

    def _pick_spot(self, state: SpatialCharacter, kinds: tuple[str, ...], salt: str) -> ActivitySpot:
        spots = self._location_spots(state.location_id)
        matching = [spot for spot in spots if spot.kind in kinds or any(verb in kinds for verb in spot.verbs)] or spots
        index = int(self._number(f"{state.character_id}:{salt}:{state.revision}", 0, 10000)) % len(matching)
        return matching[index]

    def _step(self, spot: ActivitySpot, label: str, activity: str, duration: int = 1, target_id: str | None = None) -> RoutineStep:
        return RoutineStep(label, activity, spot.x, spot.z, spot.id, duration, target_id)

    def _plan(self, world: World, state: SpatialCharacter, action: Action | None) -> list[RoutineStep]:
        kind = action.kind if action else None
        target_id = action.target_id if action else None
        for adventure in world.adventures.values():
            for target in adventure.story.get('targets', []):
                if kind is ActionKind.INSPECT and target_id == target['id']:
                    return [RoutineStep(target['label'], 'using', target['x'], target['z'],
                                        duration=3, target_id=target_id)]
        if kind in {ActionKind.TALK, ActionKind.HELP, ActionKind.LIE} and target_id in self.characters:
            target = self.characters[target_id]
            return [
                RoutineStep(f"Walk over to {world.characters[target_id].name}", "approaching", target.x, target.z, duration=0, target_id=target_id),
                RoutineStep("Share a moment together", kind.value, target.x, target.z, duration=2, target_id=target_id),
                RoutineStep("React before moving on", "reacting", target.x + 1.4, target.z, duration=1, target_id=target_id),
            ]
        mapping = {
            ActionKind.INSPECT: (("curiosity", "machine", "memory", "danger"), "Inspect the point of interest", "inspecting", 2),
            ActionKind.SEARCH: (("curiosity", "creative", "danger"), "Search the surroundings", "searching", 2),
            ActionKind.EXPLORE: (("travel", "curiosity", "adventure"), "Explore beyond the obvious path", "exploring", 1),
            ActionKind.REST: (("rest", "social"), "Settle somewhere comfortable", "resting", 2),
            ActionKind.SLEEP: (("rest", "personal"), "Find a quiet place to sleep", "sleeping", 3),
            ActionKind.PICK_UP: (("creative", "curiosity", "food"), "Collect a useful prop", "collecting", 1),
            ActionKind.DROP: (("creative", "social"), "Put the prop down", "placing", 1),
            ActionKind.USE_ITEM: (("machine", "creative", "food", "game"), "Use the carried prop", "using", 2),
            ActionKind.MOVE: (("travel", "adventure"), "Get oriented after arriving", "arriving", 1),
        }
        kinds, label, activity, duration = mapping.get(kind, (("social", "rest", "performance"), "Choose what to do next", "observing", 1))
        first = self._pick_spot(state, kinds, action.kind.value if action else "daily")
        second = self._pick_spot(state, ("social", "performance", "rest", "adventure"), "followup")
        steps = [self._step(first, label, activity, duration, target_id)]
        if kind in {ActionKind.SEARCH, ActionKind.EXPLORE, ActionKind.INSPECT} and second.id != first.id:
            steps.append(self._step(second, "Compare it with another part of the room", "considering", 1))
        return steps

    def _advance_character(self, world: World, state: SpatialCharacter) -> None:
        if not state.plan or state.plan_index >= len(state.plan):
            state.phase = "idle"
            return
        step = state.plan[state.plan_index]
        if step.target_id in self.characters:
            target = self.characters[step.target_id]
            if target.location_id == state.location_id:
                step.x, step.z = target.x, target.z
        dx, dz = step.x - state.x, step.z - state.z
        distance = math.hypot(dx, dz)
        if distance > 0.18:
            stride = min(2.6, distance)
            state.x = round(state.x + dx / distance * stride, 3)
            state.z = round(state.z + dz / distance * stride, 3)
            state.phase = "walking"
            state.activity = step.activity
            return
        state.x, state.z = step.x, step.z
        state.phase = "acting"
        state.activity = step.activity
        if state.dwell < 0:
            state.dwell = step.duration
        if state.dwell > 0:
            state.dwell -= 1
            return
        state.plan_index += 1
        state.dwell = -1

    def perception_for(self, character_id: str) -> dict[str, Any]:
        if not self.enabled:
            return {}
        state = self.characters.get(character_id)
        if not state:
            return {}
        spots = self._location_spots(state.location_id)
        distances = {
            other_id: round(math.hypot(other.x - state.x, other.z - state.z), 2)
            for other_id, other in self.characters.items()
            if other_id != character_id and other.location_id == state.location_id
        }
        return {
            "activity": state.activity,
            "phase": state.phase,
            "available_spots": tuple(spot.label for spot in spots),
            "character_distances": distances,
        }

    def public_state(self) -> dict[str, Any]:
        occupied: dict[str, int] = {}
        for state in self.characters.values():
            if state.plan_index < len(state.plan):
                spot_id = state.plan[state.plan_index].spot_id
                if spot_id:
                    occupied[spot_id] = occupied.get(spot_id, 0) + 1
        return {
            "enabled": self.enabled,
            "director": {
                "location_id": self.director.location_id,
                "position": {"x": self.director.x, "z": self.director.z},
                "target": {"x": self.director.x, "z": self.director.z},
                "target_id": self.director.target_id,
                "phase": self.director.phase,
                "revision": self.director.revision,
                "check_count": self.director.check_count,
            },
            "activity_spots": [
                {**asdict(spot), "verbs": list(spot.verbs), "occupied": occupied.get(spot.id, 0)}
                for spot in self.spots.values()
            ],
            "characters": {
                character_id: {
                    "location_id": state.location_id,
                    "position": {"x": state.x, "z": state.z},
                    "target": (
                        {"x": state.plan[state.plan_index].x, "z": state.plan[state.plan_index].z}
                        if state.plan_index < len(state.plan) else {"x": state.x, "z": state.z}
                    ),
                    "spot_id": (
                        state.plan[state.plan_index].spot_id if state.plan_index < len(state.plan) else None
                    ),
                    "target_id": (
                        state.plan[state.plan_index].target_id if state.plan_index < len(state.plan) else None
                    ),
                    "activity": state.activity,
                    "phase": state.phase,
                    "revision": state.revision,
                    "plan": [
                        {"label": step.label, "activity": step.activity, "status": (
                            "complete" if index < state.plan_index else "active" if index == state.plan_index else "next"
                        )}
                        for index, step in enumerate(state.plan)
                    ],
                }
                for character_id, state in self.characters.items()
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "director": asdict(self.director),
            "characters": {
                character_id: {
                    "location_id": state.location_id, "x": state.x, "z": state.z,
                    "plan": [asdict(step) for step in state.plan], "plan_index": state.plan_index,
                    "phase": state.phase, "activity": state.activity, "dwell": state.dwell,
                    "revision": state.revision,
                }
                for character_id, state in self.characters.items()
            },
        }

    @classmethod
    def from_dict(cls, world: World, raw: dict[str, Any] | None, *, enabled: bool = True) -> LivingWorld:
        living = cls(world, enabled=bool((raw or {}).get("enabled", enabled)))
        director = (raw or {}).get("director", {})
        if isinstance(director, dict):
            defaults = asdict(living.director)
            living.director = DirectorPresence(**{
                key: director.get(key, value) for key, value in defaults.items()
            })
        for character_id, item in (raw or {}).get("characters", {}).items():
            if character_id not in living.characters:
                continue
            state = living.characters[character_id]
            state.location_id = str(item.get("location_id", state.location_id))
            state.x, state.z = float(item.get("x", state.x)), float(item.get("z", state.z))
            state.plan = [RoutineStep(**step) for step in item.get("plan", [])]
            state.plan_index = min(int(item.get("plan_index", 0)), len(state.plan))
            state.phase, state.activity = str(item.get("phase", "idle")), str(item.get("activity", "observing"))
            state.dwell, state.revision = int(item.get("dwell", -1)), int(item.get("revision", 0))
        return living
