"""Authoritative state, local perception, validation, and tool execution."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from autonomous_ai_world.events import EventBus
from autonomous_ai_world.models import (
    Action,
    ActionKind,
    ActionResult,
    Adventure,
    AdventurePhase,
    AdventureStatus,
    Character,
    DirectorEventKind,
    DirectorEventRequest,
    Event,
    EventKind,
    KnowledgeFact,
    Location,
    Perception,
    Weather,
    WorldObject,
    WorldTime,
    QuestObjective,
)


class World:
    """The only component authorized to change physical or environmental state."""

    _ENERGY_COST = {
        ActionKind.MOVE: 2,
        ActionKind.TALK: 1,
        ActionKind.INSPECT: 1,
        ActionKind.EXPLORE: 2,
        ActionKind.SEARCH: 2,
        ActionKind.PICK_UP: 1,
        ActionKind.DROP: 0,
        ActionKind.USE_ITEM: 1,
        ActionKind.HELP: 1,
        ActionKind.LIE: 1,
    }

    def __init__(
        self,
        locations: Iterable[Location],
        characters: Iterable[Character],
        event_bus: EventBus | None = None,
        *,
        objects: Iterable[WorldObject] = (),
        world_time: WorldTime | None = None,
        weather: Weather = Weather.CLEAR,
        adventures: Iterable[Adventure] = (),
    ) -> None:
        location_list = list(locations)
        character_list = list(characters)
        object_list = list(objects)
        self.locations = {location.id: location for location in location_list}
        self.characters = {character.id: character for character in character_list}
        self.objects = {obj.id: obj for obj in object_list}
        adventure_list = list(adventures)
        self.adventures = {adventure.id: adventure for adventure in adventure_list}
        if len(self.locations) != len(location_list):
            raise ValueError("location ids must be unique")
        if len(self.characters) != len(character_list):
            raise ValueError("character ids must be unique")
        if len(self.objects) != len(object_list):
            raise ValueError("object ids must be unique")
        if len(self.adventures) != len(adventure_list):
            raise ValueError("adventure ids must be unique")
        self.events = event_bus or EventBus()
        self.tick = 0
        self.time = world_time or WorldTime()
        self.weather = weather
        self.living_world = None
        self._sequence = 0
        self._validate_initial_state()

    def _validate_initial_state(self) -> None:
        if not self.locations:
            raise ValueError("The world requires at least one location")
        for location in self.locations.values():
            missing = location.exits.difference(self.locations)
            if missing:
                raise ValueError(f"{location.id} has unknown exits: {sorted(missing)}")
        for character in self.characters.values():
            if character.location_id not in self.locations:
                raise ValueError(
                    f"{character.id} starts in unknown location {character.location_id}"
                )
            for object_id in character.inventory:
                if object_id not in self.objects:
                    raise ValueError(f"{character.id} holds unknown object {object_id}")
                if self.objects[object_id].held_by != character.id:
                    raise ValueError(f"inventory ownership mismatch for {object_id}")
        for obj in self.objects.values():
            if obj.location_id is not None and obj.location_id not in self.locations:
                raise ValueError(f"{obj.id} is in unknown location {obj.location_id}")
            if obj.held_by is not None and obj.held_by not in self.characters:
                raise ValueError(f"{obj.id} is held by unknown character {obj.held_by}")
        for adventure in self.adventures.values():
            if adventure.origin_location_id not in self.locations:
                raise ValueError(f"{adventure.id} has an unknown origin")
            if adventure.hidden_location_id not in self.locations:
                raise ValueError(f"{adventure.id} has an unknown hidden location")

    def advance_tick(self, minutes: int = 10) -> int:
        if minutes <= 0:
            raise ValueError("tick duration must be positive")
        self.tick += 1
        self.time.advance(minutes)
        for character in self.characters.values():
            character.physical_state.hunger = min(100, character.physical_state.hunger + 1)
            character.emotions.settle()
        return self.tick

    def perceive(self, character_id: str) -> Perception:
        character = self.characters[character_id]
        location = self.locations[character.location_id]
        nearby = tuple(
            sorted(
                other.id
                for other in self.characters.values()
                if other.id != character_id and other.location_id == character.location_id
            )
        )
        visible_objects = {
            obj.id: obj.description
            for obj in self.objects.values()
            if obj.location_id == location.id
            and (not obj.hidden or character_id in obj.discovered_by)
        }
        recent = tuple(
            event
            for event in self.events.history[-20:]
            if event.location_id == character.location_id
            or event.actor_id == character_id
            or event.data.get("target_id") == character_id
        )
        known_adventures = tuple(
            {
                "id": adventure.id,
                "title": adventure.title,
                "premise": adventure.premise,
                "stakes": adventure.stakes,
                "quest_objective": adventure.quest_objective,
                "generated_world": "yes" if adventure.generated_location_ids else "no",
                "objective_target_id": next(
                    (objective.target_id for objective in adventure.objectives if objective.status == "pending"),
                    "",
                ),
                "phase": adventure.phase.value,
                "origin_location_id": adventure.origin_location_id,
                "hidden_location_id": (
                    adventure.hidden_location_id
                    if adventure.phase
                    in {
                        AdventurePhase.DISCOVERY,
                        AdventurePhase.ESCALATION,
                        AdventurePhase.RESOLUTION,
                    }
                    else "unknown"
                ),
                "next_location_id": (
                    self._next_step(character.location_id, adventure.origin_location_id)
                    if adventure.phase in {AdventurePhase.HOOK, AdventurePhase.INVESTIGATION}
                    else self._next_step(character.location_id, adventure.hidden_location_id)
                    if adventure.phase is AdventurePhase.DISCOVERY
                    else self._next_step(
                        character.location_id,
                        adventure.generated_location_ids[-1]
                        if adventure.generated_location_ids
                        else adventure.hidden_location_id,
                    )
                    if adventure.phase is AdventurePhase.ESCALATION
                    else ""
                ) or "",
            }
            for adventure in self.adventures.values()
            if adventure.status is AdventureStatus.ACTIVE
            and f"adventure:{adventure.id}" in character.knowledge
        )
        pocket_ids = {
            location_id
            for adventure in self.adventures.values()
            for location_id in adventure.generated_location_ids
        }
        active_pocket_ids = {
            location_id
            for adventure in self.adventures.values()
            if adventure.status is AdventureStatus.ACTIVE
            for location_id in adventure.generated_location_ids
        }
        is_pocket_world = character.location_id in pocket_ids
        homeward_exit_id = (
            self._next_exit_toward_hub(character.location_id, pocket_ids)
            if is_pocket_world and character.location_id not in active_pocket_ids
            else None
        )
        spatial = self.living_world.perception_for(character_id) if self.living_world else {}
        return Perception(
            tick=self.tick,
            location_id=location.id,
            location_name=location.name,
            description=location.description,
            exits=tuple(sorted(location.exits)),
            nearby_characters=nearby,
            features=location.features,
            energy=character.energy,
            recent_events=recent,
            time_label=self.time.label,
            is_night=self.time.is_night,
            weather=self.weather,
            visible_objects=visible_objects,
            inventory=tuple(character.inventory),
            known_facts=tuple(character.knowledge.values()),
            location_danger=location.danger,
            nearby_energy={
                other_id: self.characters[other_id].energy for other_id in nearby
            },
            hunger=character.physical_state.hunger,
            inventory_tags={
                object_id: tuple(sorted(self.objects[object_id].tags))
                for object_id in character.inventory
                if object_id in self.objects
            },
            inventory_uses={
                object_id: self.objects[object_id].uses_remaining
                for object_id in character.inventory
                if object_id in self.objects
            },
            active_adventures=known_adventures,
            is_pocket_world=is_pocket_world,
            homeward_exit_id=homeward_exit_id,
            current_activity=str(spatial.get("activity", "observing")),
            activity_phase=str(spatial.get("phase", "idle")),
            available_activity_spots=tuple(spatial.get("available_spots", ())),
            nearby_distances=dict(spatial.get("character_distances", {})),
        )

    def _next_exit_toward_hub(self, start_id: str, pocket_ids: set[str]) -> str | None:
        queue: list[tuple[str, str | None]] = [(start_id, None)]
        visited = {start_id}
        for location_id, first_step in queue:
            if location_id not in pocket_ids:
                return first_step
            for neighbor in sorted(self.locations[location_id].exits):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, first_step or neighbor))
        return None

    def _next_step(self, start_id: str, destination_id: str) -> str | None:
        if start_id == destination_id:
            return None
        queue: list[tuple[str, str | None]] = [(start_id, None)]
        visited = {start_id}
        for location_id, first_step in queue:
            for neighbor in sorted(self.locations[location_id].exits):
                if neighbor in visited:
                    continue
                step = first_step or neighbor
                if neighbor == destination_id:
                    return step
                visited.add(neighbor)
                queue.append((neighbor, step))
        return None

    def start_adventure(
        self,
        adventure: Adventure,
        *,
        pocket_zones: tuple[Mapping[str, object], ...] = (),
    ) -> Event:
        """Atomically seed a validated premise; no character action is selected."""
        if adventure.id in self.adventures:
            raise ValueError(f"adventure '{adventure.id}' already exists")
        if any(item.status is AdventureStatus.ACTIVE for item in self.adventures.values()):
            raise ValueError("only one prototype adventure may be active")
        if adventure.origin_location_id not in self.locations:
            raise ValueError("adventure origin does not exist")
        planned_locations: list[Location] = []
        if pocket_zones:
            for index, zone in enumerate(pocket_zones):
                suffix = str(zone.get("slug", f"zone_{index + 1}"))
                location_id = f"pocket_{adventure.id}_{suffix}"
                if location_id in self.locations or any(item.id == location_id for item in planned_locations):
                    raise ValueError("generated pocket-world location id already exists")
                planned_locations.append(
                    Location(
                        location_id,
                        str(zone.get("name", suffix.replace("_", " ").title())),
                        str(zone.get("description", "A newly generated pocket-world zone.")),
                        features={str(key): str(value) for key, value in dict(zone.get("features", {})).items()},
                        danger=float(zone.get("danger", 0.35)),
                    )
                )
            if len(planned_locations) < 3:
                raise ValueError("a generated adventure world requires at least three zones")
            for index, location in enumerate(planned_locations):
                if index:
                    location.exits.add(planned_locations[index - 1].id)
                if index + 1 < len(planned_locations):
                    location.exits.add(planned_locations[index + 1].id)
            adventure.hidden_location_id = planned_locations[0].id
            adventure.generated_location_ids = [location.id for location in planned_locations]
        elif adventure.hidden_location_id not in self.locations:
            raise ValueError("adventure hidden location does not exist")
        if adventure.origin_location_id == adventure.hidden_location_id:
            raise ValueError("adventure locations must differ")
        origin = self.locations[adventure.origin_location_id]
        if adventure.hook_feature_id in origin.features:
            raise ValueError("adventure hook id already exists")
        if adventure.clue_object_id in self.objects:
            raise ValueError("adventure clue id already exists")
        if adventure.hidden_location_id in origin.exits:
            raise ValueError("adventure hidden location must initially be inaccessible")

        self.locations.update({location.id: location for location in planned_locations})

        adventure.phase = AdventurePhase.HOOK
        adventure.status = AdventureStatus.ACTIVE
        adventure.created_tick = self.tick
        adventure.created_day = self.time.day
        adventure.last_progress_tick = self.tick
        if not adventure.objectives:
            adventure.objectives = [
                QuestObjective(f"{adventure.id}:briefing", "Inspect Caine's adventure briefing.", "inspect", adventure.hook_feature_id),
                QuestObjective(f"{adventure.id}:key", "Discover the portal key hidden near the briefing.", "discover", adventure.clue_object_id),
                QuestObjective(f"{adventure.id}:enter", "Enter the generated pocket world.", "travel", adventure.hidden_location_id),
                QuestObjective(f"{adventure.id}:finale", adventure.quest_objective, "resolve", adventure.escalation_feature_id),
            ]
        self.adventures[adventure.id] = adventure
        origin.features[adventure.hook_feature_id] = adventure.hook_description
        self.objects[adventure.clue_object_id] = WorldObject(
            adventure.clue_object_id,
            adventure.clue_name,
            adventure.clue_description,
            adventure.origin_location_id,
            portable=True,
            hidden=True,
            tags={"adventure_clue", f"adventure:{adventure.id}"},
        )
        event = self._event(
            EventKind.ADVENTURE_STARTED,
            None,
            f"Adventure begins - {adventure.title}: {adventure.premise}",
            {
                "adventure_id": adventure.id,
                "title": adventure.title,
                "premise": adventure.premise,
                "feature_id": adventure.hook_feature_id,
                "description": adventure.hook_description,
                "phase": adventure.phase.value,
                "world_theme": adventure.world_theme,
                "quest_objective": adventure.quest_objective,
                "generated_location_ids": list(adventure.generated_location_ids),
                "objectives": [objective.description for objective in adventure.objectives],
            },
            location_id=adventure.origin_location_id,
            importance=0.9,
        )
        adventure.event_sequences.append(event.sequence)
        self.events.publish(event)
        return event

    def advance_adventure(
        self,
        adventure_id: str,
        new_phase: AdventurePhase,
        *,
        actor_id: str,
        cause_event_sequence: int,
    ) -> Event:
        """Apply one rule-defined phase transition after a real character event."""
        adventure = self.adventures.get(adventure_id)
        if adventure is None or adventure.status is not AdventureStatus.ACTIVE:
            raise ValueError("adventure is not active")
        allowed = {
            AdventurePhase.HOOK: AdventurePhase.INVESTIGATION,
            AdventurePhase.INVESTIGATION: AdventurePhase.DISCOVERY,
            AdventurePhase.DISCOVERY: AdventurePhase.ESCALATION,
            AdventurePhase.ESCALATION: AdventurePhase.RESOLUTION,
        }
        if allowed.get(adventure.phase) is not new_phase:
            raise ValueError(
                f"invalid adventure transition {adventure.phase.value} -> {new_phase.value}"
            )
        actor = self.characters.get(actor_id)
        if actor is None:
            raise ValueError("adventure progress requires a real character actor")
        cause = next(
            (
                event
                for event in self.events.history
                if event.sequence == cause_event_sequence
            ),
            None,
        )
        if cause is None or cause.actor_id != actor_id:
            raise ValueError("adventure progress requires a matching causal event")
        valid_cause = {
            AdventurePhase.INVESTIGATION: (
                cause.kind is EventKind.INSPECTED
                and cause.data.get("target_id") == adventure.hook_feature_id
            )
            or (
                cause.kind is EventKind.OBJECT_DISCOVERED
                and cause.data.get("object_id") == adventure.clue_object_id
            ),
            AdventurePhase.DISCOVERY: (
                cause.kind is EventKind.OBJECT_DISCOVERED
                and cause.data.get("object_id") == adventure.clue_object_id
            ),
            AdventurePhase.ESCALATION: (
                cause.kind is EventKind.MOVED
                and cause.data.get("to") == adventure.hidden_location_id
            ),
            AdventurePhase.RESOLUTION: (
                cause.kind is EventKind.INSPECTED
                and cause.data.get("target_id") == adventure.escalation_feature_id
            ),
        }[new_phase]
        if not valid_cause:
            raise ValueError("causal event does not satisfy the requested transition")

        if new_phase is AdventurePhase.DISCOVERY:
            origin = self.locations[adventure.origin_location_id]
            hidden = self.locations[adventure.hidden_location_id]
            if hidden.id not in origin.exits:
                origin.exits.add(hidden.id)
                hidden.exits.add(origin.id)
        elif new_phase is AdventurePhase.ESCALATION:
            finale_id = adventure.generated_location_ids[-1] if adventure.generated_location_ids else adventure.hidden_location_id
            finale = self.locations[finale_id]
            finale.features.setdefault(
                adventure.escalation_feature_id, adventure.escalation_description
            )

        adventure.phase = new_phase
        adventure.last_progress_tick = self.tick
        adventure.participants.add(actor.id)
        objective_index = {
            AdventurePhase.INVESTIGATION: 0,
            AdventurePhase.DISCOVERY: 1,
            AdventurePhase.ESCALATION: 2,
            AdventurePhase.RESOLUTION: 3,
        }[new_phase]
        if objective_index < len(adventure.objectives):
            objective = adventure.objectives[objective_index]
            objective.status = "complete"
            objective.completed_by = actor.id
            objective.completed_tick = self.tick
        if new_phase is AdventurePhase.RESOLUTION:
            adventure.status = AdventureStatus.RESOLVED
            adventure.resolved_by = actor.id
            adventure.outcome = (
                f"{actor.name} completed the quest: {adventure.quest_objective}"
            )
            kind = EventKind.ADVENTURE_RESOLVED
            summary = f"{adventure.title} resolves: {adventure.outcome}"
        else:
            kind = EventKind.ADVENTURE_PROGRESSED
            descriptions = {
                AdventurePhase.INVESTIGATION: f"{actor.name} begins investigating {adventure.title}.",
                AdventurePhase.DISCOVERY: (
                    f"{actor.name}'s discovery reveals a path to "
                    f"{self.locations[adventure.hidden_location_id].name}."
                ),
                AdventurePhase.ESCALATION: (
                    f"{actor.name} enters {self.locations[adventure.hidden_location_id].name}; "
                    "the mystery becomes urgent."
                ),
            }
            summary = descriptions[new_phase]
        event = self._event(
            kind,
            actor,
            summary,
            {
                "adventure_id": adventure.id,
                "phase": new_phase.value,
                "cause_event_sequence": cause_event_sequence,
                "target_id": adventure.escalation_feature_id if new_phase is AdventurePhase.RESOLUTION else None,
                "objective_id": adventure.objectives[objective_index].id if objective_index < len(adventure.objectives) else None,
            },
            importance=0.85 if new_phase is not AdventurePhase.RESOLUTION else 1.0,
        )
        adventure.event_sequences.append(event.sequence)
        self.events.publish(event)
        return event

    def expire_adventure(self, adventure_id: str, reason: str) -> Event:
        adventure = self.adventures.get(adventure_id)
        if adventure is None or adventure.status is not AdventureStatus.ACTIVE:
            raise ValueError("adventure is not active")
        adventure.status = AdventureStatus.EXPIRED
        adventure.outcome = reason
        event = self._event(
            EventKind.ADVENTURE_EXPIRED,
            None,
            f"Adventure expired - {adventure.title}: {reason}",
            {"adventure_id": adventure.id, "phase": adventure.phase.value},
            location_id=adventure.origin_location_id,
            importance=0.7,
        )
        adventure.event_sequences.append(event.sequence)
        self.events.publish(event)
        return event

    def execute(self, action: Action) -> ActionResult:
        """Validate and, only if valid, apply an agent's requested tool action."""
        error = self._validation_error(action)
        if error:
            return self._reject(action, error)
        handlers = {
            ActionKind.MOVE: self._move,
            ActionKind.TALK: self._talk,
            ActionKind.INSPECT: self._inspect,
            ActionKind.REST: self._rest,
            ActionKind.EXPLORE: self._explore,
            ActionKind.SEARCH: self._search,
            ActionKind.PICK_UP: self._pick_up,
            ActionKind.DROP: self._drop,
            ActionKind.USE_ITEM: self._use_item,
            ActionKind.SLEEP: self._sleep,
            ActionKind.HELP: self._help,
            ActionKind.LIE: self._lie,
        }
        event = handlers[action.kind](action)
        actor = self.characters[action.actor_id]
        result = ActionResult(accepted=True, event=event)
        actor.last_action = action
        actor.last_action_result = result
        self.events.publish(event)
        return result

    def _validation_error(self, action: Action) -> str | None:
        if not isinstance(action.kind, ActionKind):
            return f"unsupported action kind '{action.kind}'"
        actor = self.characters.get(action.actor_id)
        if actor is None:
            return f"unknown actor '{action.actor_id}'"
        cost = self._ENERGY_COST.get(action.kind, 0)
        if actor.energy < cost:
            return f"{actor.name} is too tired to {action.kind.value}"
        location = self.locations[actor.location_id]
        if action.kind is ActionKind.MOVE:
            if not action.target_id:
                return "move requires a target location"
            if action.target_id not in self.locations:
                return f"unknown location '{action.target_id}'"
            if action.target_id not in location.exits:
                return f"{self.locations[action.target_id].name} is not adjacent"
        elif action.kind in {ActionKind.TALK, ActionKind.HELP, ActionKind.LIE}:
            target = self.characters.get(action.target_id or "")
            if target is None:
                return f"unknown character '{action.target_id}'"
            if target.id == actor.id:
                return "a character cannot target themself"
            if target.location_id != actor.location_id:
                return f"{target.name} is not here"
            if action.kind in {ActionKind.TALK, ActionKind.LIE} and (
                not action.message or not action.message.strip()
            ):
                return f"{action.kind.value} requires a message"
        elif action.kind is ActionKind.INSPECT:
            if not action.target_id:
                return "inspect requires a target"
            local_targets = set(location.features) | {location.id}
            local_targets.update(self.perceive(actor.id).visible_objects)
            local_targets.update(
                char.id
                for char in self.characters.values()
                if char.location_id == actor.location_id and char.id != actor.id
            )
            if action.target_id not in local_targets:
                return f"'{action.target_id}' cannot be perceived here"
        elif action.kind is ActionKind.PICK_UP:
            obj = self.objects.get(action.target_id or "")
            if obj is None or obj.id not in self.perceive(actor.id).visible_objects:
                return f"'{action.target_id}' cannot be picked up here"
            if not obj.portable:
                return f"{obj.name} is not portable"
            if obj.held_by is not None:
                return f"{obj.name} is already held"
        elif action.kind in {ActionKind.DROP, ActionKind.USE_ITEM}:
            if not action.target_id or action.target_id not in actor.inventory:
                return f"'{action.target_id}' is not in {actor.name}'s inventory"
            if action.target_id not in self.objects:
                return f"unknown inventory object '{action.target_id}'"
            if (
                action.kind is ActionKind.USE_ITEM
                and self.objects[action.target_id].uses_remaining == 0
            ):
                return f"{self.objects[action.target_id].name} has no uses remaining"
        return None

    def _move(self, action: Action) -> Event:
        actor = self.characters[action.actor_id]
        origin_id = actor.location_id
        actor.location_id = action.target_id or origin_id
        actor.energy -= self._ENERGY_COST[ActionKind.MOVE]
        destination = self.locations[actor.location_id]
        return self._event(
            EventKind.MOVED,
            actor,
            f"{actor.name} walks from {self.locations[origin_id].name} to {destination.name}.",
            {"from": origin_id, "to": destination.id},
            importance=0.4,
        )

    def _talk(self, action: Action) -> Event:
        return self._social_event(action, EventKind.SPOKE, "tells", 0.45)

    def _lie(self, action: Action) -> Event:
        return self._social_event(action, EventKind.LIED, "deceives", 0.75)

    def _social_event(
        self, action: Action, kind: EventKind, verb: str, importance: float
    ) -> Event:
        actor = self.characters[action.actor_id]
        target = self.characters[action.target_id or ""]
        actor.energy -= self._ENERGY_COST[action.kind]
        message = (action.message or "").strip()
        return self._event(
            kind,
            actor,
            f'{actor.name} {verb} {target.name}, "{message}"',
            {"target_id": target.id, "message": message},
            importance=importance,
        )

    def _inspect(self, action: Action) -> Event:
        actor = self.characters[action.actor_id]
        actor.energy -= self._ENERGY_COST[ActionKind.INSPECT]
        target_id = action.target_id or ""
        location = self.locations[actor.location_id]
        if target_id == location.id:
            detail = location.description
        elif target_id in location.features:
            detail = location.features[target_id]
        elif target_id in self.objects:
            detail = self.objects[target_id].description
        else:
            detail = f"{self.characters[target_id].name} seems occupied with the world around them."
        return self._event(
            EventKind.INSPECTED,
            actor,
            f"{actor.name} inspects {target_id}: {detail}",
            {"target_id": target_id, "detail": detail},
            importance=0.5,
        )

    def _rest(self, action: Action) -> Event:
        actor = self.characters[action.actor_id]
        before = actor.energy
        actor.energy = min(actor.max_energy, actor.energy + 4)
        return self._event(
            EventKind.RESTED,
            actor,
            f"{actor.name} rests at {self.locations[actor.location_id].name} "
            f"and recovers {actor.energy - before} energy.",
            {"energy_before": before, "energy_after": actor.energy},
            importance=0.2,
        )

    def _sleep(self, action: Action) -> Event:
        actor = self.characters[action.actor_id]
        before = actor.energy
        actor.energy = actor.max_energy
        actor.physical_state.hunger = min(100, actor.physical_state.hunger + 3)
        return self._event(
            EventKind.SLEPT,
            actor,
            f"{actor.name} sleeps at {self.locations[actor.location_id].name}.",
            {"energy_before": before, "energy_after": actor.energy},
            importance=0.25,
        )

    def _explore(self, action: Action) -> Event:
        actor = self.characters[action.actor_id]
        actor.energy -= self._ENERGY_COST[ActionKind.EXPLORE]
        location = self.locations[actor.location_id]
        if location.features:
            found = sorted(location.features)[(self.tick + self._sequence) % len(location.features)]
            detail = f"notices {found}"
        else:
            found = None
            detail = "finds no obvious clue"
        return self._event(
            EventKind.EXPLORED,
            actor,
            f"{actor.name} explores {location.name} and {detail}.",
            {"found": found},
            importance=0.35,
        )

    def _search(self, action: Action) -> Event:
        actor = self.characters[action.actor_id]
        actor.energy -= self._ENERGY_COST[ActionKind.SEARCH]
        hidden = sorted(
            (
                obj
                for obj in self.objects.values()
                if obj.location_id == actor.location_id
                and obj.hidden
                and actor.id not in obj.discovered_by
            ),
            key=lambda obj: obj.id,
        )
        if hidden:
            obj = hidden[0]
            obj.hidden = False
            obj.discovered_by.add(actor.id)
            actor.knowledge[f"object:{obj.id}"] = KnowledgeFact(
                f"object:{obj.id}",
                f"{obj.name} is at {self.locations[actor.location_id].name}.",
                self.tick,
                "discovery",
            )
            return self._event(
                EventKind.OBJECT_DISCOVERED,
                actor,
                f"{actor.name} searches {self.locations[actor.location_id].name} "
                f"and discovers {obj.name}.",
                {"object_id": obj.id},
                importance=0.75,
            )
        return self._event(
            EventKind.SEARCHED,
            actor,
            f"{actor.name} searches {self.locations[actor.location_id].name} but finds nothing hidden.",
            {},
            importance=0.25,
        )

    def _pick_up(self, action: Action) -> Event:
        actor = self.characters[action.actor_id]
        obj = self.objects[action.target_id or ""]
        actor.energy -= self._ENERGY_COST[ActionKind.PICK_UP]
        obj.location_id = None
        obj.held_by = actor.id
        actor.inventory.append(obj.id)
        return self._event(
            EventKind.ITEM_PICKED_UP,
            actor,
            f"{actor.name} picks up {obj.name}.",
            {"object_id": obj.id},
            importance=0.55,
        )

    def _drop(self, action: Action) -> Event:
        actor = self.characters[action.actor_id]
        obj = self.objects[action.target_id or ""]
        actor.inventory.remove(obj.id)
        obj.held_by = None
        obj.location_id = actor.location_id
        return self._event(
            EventKind.ITEM_DROPPED,
            actor,
            f"{actor.name} drops {obj.name} at {self.locations[actor.location_id].name}.",
            {"object_id": obj.id},
            importance=0.4,
        )

    def _use_item(self, action: Action) -> Event:
        actor = self.characters[action.actor_id]
        obj = self.objects[action.target_id or ""]
        actor.energy -= self._ENERGY_COST[ActionKind.USE_ITEM]
        if obj.uses_remaining is not None and obj.uses_remaining > 0:
            obj.uses_remaining -= 1
        if "food" in obj.tags:
            actor.physical_state.hunger = max(0, actor.physical_state.hunger - 25)
        return self._event(
            EventKind.ITEM_USED,
            actor,
            f"{actor.name} uses {obj.name}.",
            {
                "object_id": obj.id,
                "uses_remaining": obj.uses_remaining,
                "hunger_after": actor.physical_state.hunger,
            },
            importance=0.5,
        )

    def _help(self, action: Action) -> Event:
        actor = self.characters[action.actor_id]
        target = self.characters[action.target_id or ""]
        actor.energy -= self._ENERGY_COST[ActionKind.HELP]
        before = target.energy
        target.energy = min(target.max_energy, target.energy + 2)
        return self._event(
            EventKind.HELPED,
            actor,
            f"{actor.name} helps {target.name}, who recovers {target.energy - before} energy.",
            {"target_id": target.id, "energy_after": target.energy},
            importance=0.8,
        )

    def apply_director_event(self, request: DirectorEventRequest) -> Event:
        """Validate a Director proposal before modifying the environment."""
        if not isinstance(request.kind, DirectorEventKind):
            raise ValueError("unsupported Director event kind")
        if request.kind is DirectorEventKind.WEATHER:
            if request.weather is None or not isinstance(request.weather, Weather):
                raise ValueError("weather event requires valid weather")
            if request.weather is self.weather:
                raise ValueError("weather event must change current weather")
            before = self.weather
            self.weather = request.weather
            event = self._event(
                EventKind.WEATHER_CHANGED,
                None,
                f"Director: weather changes from {before.value} to {self.weather.value}.",
                {"before": before.value, "after": self.weather.value, "title": request.title},
                importance=0.7,
            )
        elif request.kind is DirectorEventKind.OBJECT:
            if not request.location_id or request.location_id not in self.locations:
                raise ValueError("object event requires a valid location")
            if not request.object_id or request.object_id in self.objects:
                raise ValueError("object event requires a unique object id")
            obj = WorldObject(
                request.object_id,
                request.title,
                request.description,
                request.location_id,
                portable=True,
            )
            self.objects[obj.id] = obj
            event = self._event(
                EventKind.ENVIRONMENT_CHANGED,
                None,
                f"Director: {request.title} appears at {self.locations[request.location_id].name}.",
                {"object_id": obj.id, "director_kind": request.kind.value, "title": request.title},
                location_id=request.location_id,
                importance=0.75,
            )
        elif request.kind is DirectorEventKind.OPEN_PATH:
            if not request.location_id or request.location_id not in self.locations:
                raise ValueError("path event requires a valid source location")
            if not request.destination_id or request.destination_id not in self.locations:
                raise ValueError("path event requires a valid destination location")
            if request.destination_id == request.location_id:
                raise ValueError("path endpoints must be different")
            if request.destination_id in self.locations[request.location_id].exits:
                raise ValueError("path already exists")
            self.locations[request.location_id].exits.add(request.destination_id)
            self.locations[request.destination_id].exits.add(request.location_id)
            event = self._event(
                EventKind.ENVIRONMENT_CHANGED,
                None,
                f"Director: {request.title}",
                {
                    "from": request.location_id,
                    "to": request.destination_id,
                    "director_kind": request.kind.value,
                    "title": request.title,
                },
                location_id=request.location_id,
                importance=0.8,
            )
        else:
            if not request.location_id or request.location_id not in self.locations:
                raise ValueError("situation requires a valid location")
            feature_id = request.object_id or f"situation_{self._sequence + 1}"
            if feature_id in self.locations[request.location_id].features:
                raise ValueError("situation id already exists")
            self.locations[request.location_id].features[feature_id] = request.description
            event = self._event(
                EventKind.SITUATION_CREATED,
                None,
                f"Director: {request.title} at {self.locations[request.location_id].name}.",
                {
                    "feature_id": feature_id,
                    "description": request.description,
                    "director_kind": request.kind.value,
                    "title": request.title,
                },
                location_id=request.location_id,
                importance=0.7,
            )
        self.events.publish(event)
        return event

    def create_situation(
        self, *, location_id: str, feature_id: str, description: str, title: str
    ) -> Event:
        return self.apply_director_event(
            DirectorEventRequest(
                DirectorEventKind.SITUATION,
                title,
                location_id=location_id,
                description=description,
                object_id=feature_id,
            )
        )

    def _reject(self, action: Action, reason: str) -> ActionResult:
        actor = self.characters.get(action.actor_id)
        action_name = action.kind.value if isinstance(action.kind, ActionKind) else str(action.kind)
        event = self._event(
            EventKind.ACTION_REJECTED,
            actor,
            f"Rejected {action_name} from {action.actor_id}: {reason}.",
            {"reason": reason, "requested_target": action.target_id},
            location_id=actor.location_id if actor else None,
            importance=0.45,
        )
        result = ActionResult(accepted=False, event=event)
        if actor:
            actor.last_action = action
            actor.last_action_result = result
        self.events.publish(event)
        return result

    def _event(
        self,
        kind: EventKind,
        actor: Character | None,
        summary: str,
        data: dict[str, object],
        *,
        location_id: str | None = None,
        importance: float = 0.3,
    ) -> Event:
        self._sequence += 1
        return Event(
            sequence=self._sequence,
            tick=self.tick,
            kind=kind,
            actor_id=actor.id if actor else None,
            location_id=location_id or (actor.location_id if actor else None),
            summary=summary,
            data=data,
            importance=importance,
        )
