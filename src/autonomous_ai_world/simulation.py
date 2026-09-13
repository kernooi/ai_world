"""Async orchestration, deterministic state projection, and persistence."""

from __future__ import annotations

import asyncio
import random
from dataclasses import asdict
from typing import Any

from autonomous_ai_world.adventures import AdventureManager
from autonomous_ai_world.agents import AgentTendencies, CharacterAgent
from autonomous_ai_world.config import Settings
from autonomous_ai_world.director import DirectorAgent
from autonomous_ai_world.memory import MemoryManager
from autonomous_ai_world.models import (
    Action,
    ActionKind,
    Adventure,
    AdventurePhase,
    AdventureStatus,
    Character,
    EmotionalState,
    Event,
    EventKind,
    Goal,
    Intention,
    KnowledgeFact,
    Location,
    Personality,
    PhysicalState,
    Relationship,
    Weather,
    WorldObject,
    WorldTime,
)
from autonomous_ai_world.persistence import StateRepository
from autonomous_ai_world.relationships import RelationshipManager
from autonomous_ai_world.world import World


class Simulation:
    """Schedules independent reasoning and projects facts into private state."""

    def __init__(
        self,
        world: World,
        agents: list[CharacterAgent],
        director: DirectorAgent,
        memory: MemoryManager | None = None,
        adventures: AdventureManager | None = None,
    ) -> None:
        agent_ids = {agent.character_id for agent in agents}
        if agent_ids != set(world.characters) or len(agents) != len(agent_ids):
            raise ValueError("Every world character requires exactly one agent")
        self.world = world
        self.agents = agents
        self.director = director
        self.memory = memory or MemoryManager(tuple(world.characters))
        self.relationships = RelationshipManager(world.characters)
        self.world.events.subscribe(self._process_event)
        self.adventures = adventures
        if self.adventures:
            self.adventures.bind(world)

    async def async_step(self) -> tuple[Event, ...]:
        """Run concurrent mock-AI reasoning, then validate requests in stable order."""
        start = len(self.world.events.history)
        self.world.advance_tick()
        await self.director.update_async(self.world)
        decisions = await asyncio.gather(
            *(
                agent.decide_async(
                    self.world.perceive(agent.character_id),
                    self.world.characters[agent.character_id],
                    self.memory.store_for(agent.character_id),
                )
                for agent in self.agents
            )
        )
        # Social/inspection actions resolve before travel, reducing snapshot races while
        # preserving authoritative validation for genuine conflicts such as one item.
        order = {
            ActionKind.HELP: 0,
            ActionKind.TALK: 1,
            ActionKind.LIE: 1,
            ActionKind.INSPECT: 2,
            ActionKind.PICK_UP: 2,
            ActionKind.USE_ITEM: 2,
            ActionKind.DROP: 2,
            ActionKind.SEARCH: 3,
            ActionKind.EXPLORE: 3,
            ActionKind.REST: 3,
            ActionKind.SLEEP: 3,
            ActionKind.MOVE: 4,
        }
        for decision in sorted(decisions, key=lambda item: order[item.action.kind]):
            self.world.execute(decision.action)
        return self.world.events.history[start:]

    def step(self) -> tuple[Event, ...]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.async_step())
        raise RuntimeError("step() cannot run inside an event loop; await async_step()")

    async def async_run(self, steps: int) -> tuple[Event, ...]:
        if steps < 0:
            raise ValueError("steps cannot be negative")
        for _ in range(steps):
            await self.async_step()
        return self.world.events.history

    def run(self, steps: int) -> tuple[Event, ...]:
        if steps < 0:
            raise ValueError("steps cannot be negative")
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.async_run(steps))
        raise RuntimeError("run() cannot run inside an event loop; await async_run()")

    def _process_event(self, event: Event) -> None:
        """Deterministically update memory, knowledge, emotion, and relationships."""
        self.relationships.process(event)
        target_id = event.data.get("target_id")
        observers = {
            character.id
            for character in self.world.characters.values()
            if event.location_id is not None and character.location_id == event.location_id
        }
        if event.actor_id:
            observers.add(event.actor_id)
        if isinstance(target_id, str) and target_id in self.world.characters:
            observers.add(target_id)
        if event.kind is EventKind.WEATHER_CHANGED:
            observers = set(self.world.characters)

        participants = tuple(
            participant
            for participant in (event.actor_id, target_id if isinstance(target_id, str) else None)
            if participant
        )
        for character_id in observers:
            self.memory.store_for(character_id).remember_event(event, participants)
            character = self.world.characters[character_id]
            self._update_knowledge(character, event)
            self._update_emotions(character, event)

    def _update_knowledge(self, character: Character, event: Event) -> None:
        if event.kind is EventKind.MOVED and event.actor_id == character.id:
            destination = str(event.data["to"])
            character.knowledge[f"location:{destination}"] = KnowledgeFact(
                f"location:{destination}",
                f"{destination} is reachable and has been visited.",
                event.tick,
                "experience",
            )
        elif event.kind is EventKind.SITUATION_CREATED and event.location_id == character.location_id:
            feature_id = str(event.data["feature_id"])
            character.knowledge[f"situation:{feature_id}"] = KnowledgeFact(
                f"situation:{feature_id}",
                event.summary,
                event.tick,
                "perception",
            )
        elif event.kind is EventKind.OBJECT_DISCOVERED and event.actor_id == character.id:
            object_id = str(event.data["object_id"])
            character.knowledge[f"object:{object_id}"] = KnowledgeFact(
                f"object:{object_id}", event.summary, event.tick, "discovery"
            )
        elif event.kind in {EventKind.SPOKE, EventKind.LIED} and event.data.get("target_id") == character.id:
            character.knowledge[f"statement:{event.sequence}"] = KnowledgeFact(
                f"statement:{event.sequence}",
                f"{event.actor_id} said: {event.data.get('message', '')}",
                event.tick,
                f"told_by:{event.actor_id}",
                confidence=0.7 if event.kind is EventKind.LIED else 0.9,
            )
            for adventure_id in event.data.get("shared_adventure_ids", []):
                adventure = self.world.adventures.get(str(adventure_id))
                if adventure:
                    character.knowledge[f"adventure:{adventure.id}"] = KnowledgeFact(
                        f"adventure:{adventure.id}",
                        f"{event.actor_id} shared information about {adventure.title}.",
                        event.tick,
                        f"told_by:{event.actor_id}",
                        confidence=0.8,
                    )
        elif event.kind is EventKind.WEATHER_CHANGED:
            character.knowledge["weather:current"] = KnowledgeFact(
                "weather:current", event.summary, event.tick, "perception"
            )
        elif event.kind in {
            EventKind.ADVENTURE_STARTED,
            EventKind.ADVENTURE_PROGRESSED,
            EventKind.ADVENTURE_RESOLVED,
        }:
            adventure_id = str(event.data["adventure_id"])
            character.knowledge[f"adventure:{adventure_id}"] = KnowledgeFact(
                f"adventure:{adventure_id}", event.summary, event.tick, "experience"
            )

    @staticmethod
    def _update_emotions(character: Character, event: Event) -> None:
        is_actor = event.actor_id == character.id
        is_target = event.data.get("target_id") == character.id
        if event.kind in {EventKind.OBJECT_DISCOVERED, EventKind.SITUATION_CREATED}:
            character.emotions.adjust(curiosity=0.08, excitement=0.06)
        elif event.kind is EventKind.HELPED:
            if is_target:
                character.emotions.adjust(happiness=0.12, anxiety=-0.08, anger=-0.05)
            elif is_actor:
                character.emotions.adjust(happiness=0.05)
        elif event.kind is EventKind.LIED and is_target:
            character.emotions.adjust(anger=0.15, anxiety=0.08, happiness=-0.08)
        elif event.kind is EventKind.WEATHER_CHANGED and event.data.get("after") == Weather.STORM.value:
            character.emotions.adjust(fear=0.12, anxiety=0.12)
        elif event.kind is EventKind.ACTION_REJECTED and is_actor:
            character.emotions.adjust(anger=0.04, happiness=-0.03)
        elif event.kind is EventKind.ADVENTURE_PROGRESSED:
            character.emotions.adjust(curiosity=0.08, excitement=0.08)
        elif event.kind is EventKind.ADVENTURE_RESOLVED:
            character.emotions.adjust(happiness=0.15, excitement=0.1, anxiety=-0.12)

    def save(self, repository: StateRepository) -> None:
        repository.save(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "world": {
                "tick": self.world.tick,
                "time": asdict(self.world.time),
                "weather": self.world.weather.value,
                "locations": [
                    {
                        "id": loc.id,
                        "name": loc.name,
                        "description": loc.description,
                        "exits": sorted(loc.exits),
                        "features": dict(loc.features),
                        "danger": loc.danger,
                    }
                    for loc in self.world.locations.values()
                ],
                "objects": [
                    {
                        "id": obj.id,
                        "name": obj.name,
                        "description": obj.description,
                        "location_id": obj.location_id,
                        "portable": obj.portable,
                        "hidden": obj.hidden,
                        "discovered_by": sorted(obj.discovered_by),
                        "tags": sorted(obj.tags),
                        "uses_remaining": obj.uses_remaining,
                        "held_by": obj.held_by,
                    }
                    for obj in self.world.objects.values()
                ],
                "characters": [self._character_to_dict(char) for char in self.world.characters.values()],
                "events": [self._event_to_dict(event) for event in self.world.events.history],
                "adventures": [
                    {
                        **asdict(adventure),
                        "phase": adventure.phase.value,
                        "status": adventure.status.value,
                        "participants": sorted(adventure.participants),
                    }
                    for adventure in self.world.adventures.values()
                ],
            },
            "memory": self.memory.to_dict(),
            "director": {
                "last_intervention_tick": self.director.last_intervention_tick,
                "created": self.director._created,
            },
            "adventures_enabled": self.adventures is not None,
        }

    @classmethod
    def load(
        cls,
        repository: StateRepository,
        *,
        seed: int = 0,
        settings: Settings | None = None,
    ) -> Simulation:
        return cls.from_dict(repository.load(), seed=seed, settings=settings)

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], *, seed: int = 0, settings: Settings | None = None
    ) -> Simulation:
        raw_world = data["world"]
        locations = [
            Location(
                raw["id"], raw["name"], raw["description"],
                exits=set(raw.get("exits", [])),
                features=dict(raw.get("features", {})),
                danger=float(raw.get("danger", 0.0)),
            )
            for raw in raw_world["locations"]
        ]
        characters = [cls._character_from_dict(raw) for raw in raw_world["characters"]]
        objects = [
            WorldObject(
                raw["id"], raw["name"], raw["description"], raw.get("location_id"),
                portable=bool(raw.get("portable", False)),
                hidden=bool(raw.get("hidden", False)),
                discovered_by=set(raw.get("discovered_by", [])),
                tags=set(raw.get("tags", [])),
                uses_remaining=raw.get("uses_remaining"),
                held_by=raw.get("held_by"),
            )
            for raw in raw_world.get("objects", [])
        ]
        adventures = [
            Adventure(
                id=raw["id"],
                title=raw["title"],
                premise=raw["premise"],
                mystery=raw["mystery"],
                stakes=raw["stakes"],
                origin_location_id=raw["origin_location_id"],
                hidden_location_id=raw["hidden_location_id"],
                hook_feature_id=raw["hook_feature_id"],
                hook_description=raw["hook_description"],
                clue_object_id=raw["clue_object_id"],
                clue_name=raw["clue_name"],
                clue_description=raw["clue_description"],
                escalation_feature_id=raw["escalation_feature_id"],
                escalation_description=raw["escalation_description"],
                phase=AdventurePhase(raw["phase"]),
                status=AdventureStatus(raw["status"]),
                created_tick=int(raw["created_tick"]),
                last_progress_tick=int(raw["last_progress_tick"]),
                participants=set(raw.get("participants", [])),
                event_sequences=list(raw.get("event_sequences", [])),
                resolved_by=raw.get("resolved_by"),
                outcome=raw.get("outcome"),
            )
            for raw in raw_world.get("adventures", [])
        ]
        world = World(
            locations,
            characters,
            objects=objects,
            world_time=WorldTime(**raw_world["time"]),
            weather=Weather(raw_world["weather"]),
            adventures=adventures,
        )
        world.tick = int(raw_world["tick"])
        for raw in raw_world.get("events", []):
            event = Event(
                sequence=int(raw["sequence"]), tick=int(raw["tick"]),
                kind=EventKind(raw["kind"]), actor_id=raw.get("actor_id"),
                location_id=raw.get("location_id"), summary=raw["summary"],
                data=raw.get("data", {}), importance=float(raw.get("importance", 0.3)),
            )
            world.events.publish(event)
            world._sequence = max(world._sequence, event.sequence)
        settings = settings or Settings()
        master_rng = random.Random(seed)
        agents = [
            CharacterAgent(
                character.id,
                AgentTendencies(
                    curiosity=character.personality.curiosity,
                    sociability=character.personality.sociability,
                ),
                random.Random(master_rng.getrandbits(64)),
                provider=settings.create_provider(),
                timeout_seconds=settings.ai_timeout_seconds,
            )
            for character in characters
        ]
        adventure_manager = (
            AdventureManager(random.Random(master_rng.getrandbits(64)))
            if data.get("adventures_enabled", bool(adventures))
            else None
        )
        director = DirectorAgent(
            random.Random(master_rng.getrandbits(64)),
            provider=settings.create_provider(),
            timeout_seconds=settings.ai_timeout_seconds,
            adventure_manager=adventure_manager,
        )
        raw_director = data.get("director", {})
        director.last_intervention_tick = raw_director.get("last_intervention_tick")
        director._created = int(raw_director.get("created", 0))
        director.last_observed_tick = world.tick
        director.last_generated_event = next(
            (event for event in reversed(world.events.history) if event.actor_id is None),
            None,
        )
        memory = MemoryManager.from_dict(data.get("memory", {}))
        simulation = cls(world, agents, director, memory, adventure_manager)
        for agent in agents:
            agent._inspected = {
                (event.location_id, str(event.data["target_id"]))
                for event in world.events.history
                if event.kind is EventKind.INSPECTED
                and event.actor_id == agent.character_id
                and event.location_id is not None
            }
        return simulation

    @staticmethod
    def _character_to_dict(character: Character) -> dict[str, Any]:
        return {
            "id": character.id,
            "name": character.name,
            "location_id": character.location_id,
            "personality": asdict(character.personality),
            "values": list(character.values),
            "goals": [asdict(goal) for goal in character.goals],
            "fears": list(character.fears),
            "preferences": list(character.preferences),
            "emotions": asdict(character.emotions),
            "physical_state": asdict(character.physical_state),
            "knowledge": [asdict(fact) for fact in character.knowledge.values()],
            "relationships": {
                target_id: asdict(relationship)
                for target_id, relationship in character.relationships.items()
            },
            "current_intention": (
                {
                    **asdict(character.current_intention),
                    "action_kind": character.current_intention.action_kind.value,
                }
                if character.current_intention
                else None
            ),
            "inventory": list(character.inventory),
        }

    @staticmethod
    def _character_from_dict(raw: dict[str, Any]) -> Character:
        intention_raw = raw.get("current_intention")
        intention = (
            Intention(
                intention_raw["description"],
                ActionKind(intention_raw["action_kind"]),
                intention_raw.get("target_id"),
                float(intention_raw["priority"]),
                intention_raw["reason"],
            )
            if intention_raw
            else None
        )
        character = Character(
            raw["id"], raw["name"], raw["location_id"],
            personality=Personality(**raw.get("personality", {})),
            values=tuple(raw.get("values", [])),
            goals=[Goal(**goal) for goal in raw.get("goals", [])],
            fears=tuple(raw.get("fears", [])),
            preferences=tuple(raw.get("preferences", [])),
            emotions=EmotionalState(**raw.get("emotions", {})),
            physical_state=PhysicalState(**raw.get("physical_state", {})),
            knowledge={fact["id"]: KnowledgeFact(**fact) for fact in raw.get("knowledge", [])},
            relationships={
                target: Relationship(**relationship)
                for target, relationship in raw.get("relationships", {}).items()
            },
            current_intention=intention,
            inventory=list(raw.get("inventory", [])),
        )
        return character

    @staticmethod
    def _event_to_dict(event: Event) -> dict[str, Any]:
        return {
            "sequence": event.sequence,
            "tick": event.tick,
            "kind": event.kind.value,
            "actor_id": event.actor_id,
            "location_id": event.location_id,
            "summary": event.summary,
            "data": dict(event.data),
            "importance": event.importance,
        }


def create_default_simulation(
    seed: int | None = None,
    settings: Settings | None = None,
    *,
    enable_adventures: bool = True,
) -> Simulation:
    """Construct the small but complete Stage 7 backend demonstration."""
    master_rng = random.Random(seed)
    settings = settings or Settings()
    locations = [
        Location(
            "village", "Village",
            "A compact circle of bright houses surrounds an old stone well.",
            exits={"forest", "river"},
            features={"stone_well": "The well is deep; cool air rises from below."},
            danger=0.05,
        ),
        Location(
            "forest", "Forest",
            "Tall pines turn the paths into shifting corridors of green shade.",
            exits={"village", "cave", "river"},
            features={"broken_cart": "The cart bears fresh scratches but no wheel tracks."},
            danger=0.35,
        ),
        Location(
            "cave", "Cave",
            "A dark limestone chamber carries every sound farther than expected.",
            exits={"forest"},
            features={"wall_markings": "Loops and stars have been etched into the cave wall."},
            danger=0.7,
        ),
        Location(
            "river", "River",
            "Clear water rushes around smooth black stones beside a narrow footpath.",
            exits={"village", "forest"},
            features={"black_stones": "The stones are glassy and unusually warm."},
            danger=0.2,
        ),
        Location(
            "observatory", "Abandoned Observatory",
            "A sealed underground observatory filled with dormant brass instruments.",
            exits=set(), features={}, danger=0.65,
        ),
    ]
    alice = Character(
        "alice", "Alice", "village",
        personality=Personality(curiosity=0.9, bravery=0.8, risk_tolerance=0.75, empathy=0.75, sociability=0.65, loyalty=0.8),
        values=("friendship", "freedom", "discovery"),
        goals=[
            Goal("discover", "Discover the world's secrets", 0.9, ("discover", "explore")),
            Goal("protect_bob", "Protect Bob", 0.65, ("protect", "social"), "bob"),
        ],
        fears=("abandonment",), preferences=("mysteries", "exploration"),
    )
    bob = Character(
        "bob", "Bob", "village",
        personality=Personality(curiosity=0.45, bravery=0.65, risk_tolerance=0.7, empathy=0.35, honesty=0.3, sociability=0.8, competitiveness=0.8),
        values=("wealth", "recognition"),
        goals=[
            Goal("wealth", "Find valuable resources", 0.9, ("resource", "discover")),
            Goal("respect", "Become respected", 0.65, ("social",)),
        ],
        fears=("powerlessness",), preferences=("valuable objects", "company"),
    )
    charlie = Character(
        "charlie", "Charlie", "forest",
        personality=Personality(curiosity=0.55, bravery=0.2, risk_tolerance=0.15, empathy=0.7, honesty=0.85, sociability=0.3, patience=0.8),
        values=("safety", "honesty"),
        goals=[
            Goal("safety", "Avoid danger", 0.95, ()),
            Goal("understand", "Understand unusual signs", 0.55, ("discover",)),
        ],
        fears=("storms", "the cave"), preferences=("safe places", "careful plans"),
        emotions=EmotionalState(fear=0.35, anxiety=0.35, curiosity=0.45),
    )
    alice.relationships["bob"] = Relationship(trust=0.72, friendship=0.75, loyalty=0.65)
    bob.relationships["alice"] = Relationship(trust=0.65, friendship=0.68)
    objects = [
        WorldObject(
            "old_compass", "an old compass",
            "Its needle points toward the cave instead of north.",
            "forest", portable=True, hidden=True, tags={"mystery", "valuable"},
        ),
        WorldObject(
            "river_berries", "a pouch of river berries",
            "The blue berries smell sweet and fresh.",
            "river", portable=True, hidden=False, tags={"food"}, uses_remaining=2,
        ),
    ]
    world = World(locations, [alice, bob, charlie], objects=objects)
    agents = [
        CharacterAgent(
            character.id,
            AgentTendencies(
                curiosity=character.personality.curiosity,
                sociability=character.personality.sociability,
            ),
            random.Random(master_rng.getrandbits(64)),
            provider=settings.create_provider(),
            timeout_seconds=settings.ai_timeout_seconds,
        )
        for character in (alice, bob, charlie)
    ]
    adventure_manager = (
        AdventureManager(random.Random(master_rng.getrandbits(64)))
        if enable_adventures
        else None
    )
    director = DirectorAgent(
        random.Random(master_rng.getrandbits(64)),
        provider=settings.create_provider(),
        timeout_seconds=settings.ai_timeout_seconds,
        adventure_manager=adventure_manager,
    )
    return Simulation(world, agents, director, adventures=adventure_manager)
