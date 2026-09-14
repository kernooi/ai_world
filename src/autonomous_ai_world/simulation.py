"""Async orchestration, deterministic state projection, and persistence."""

from __future__ import annotations

import asyncio
import random
from dataclasses import asdict
from typing import Any

from autonomous_ai_world.adventures import AdventureManager, CIRCUS_ADVENTURES, DEFAULT_ADVENTURES
from autonomous_ai_world.agents import AgentTendencies, CharacterAgent
from autonomous_ai_world.config import Settings
from autonomous_ai_world.director import CIRCUS_SITUATIONS, DEFAULT_SITUATIONS, DirectorAgent
from autonomous_ai_world.episodes import EpisodeManager
from autonomous_ai_world.memory import MemoryManager
from autonomous_ai_world.living_world import LivingWorld
from autonomous_ai_world.models import (
    Action,
    ActionKind,
    Adventure,
    AdventurePhase,
    AdventureStatus,
    Belief,
    Character,
    CharacterPsychology,
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
    QuestObjective,
    Weather,
    WorldObject,
    WorldTime,
)
from autonomous_ai_world.persistence import StateRepository
from autonomous_ai_world.relationships import RelationshipManager
from autonomous_ai_world.world import World
from autonomous_ai_world.world_systems import CircusSystems


class Simulation:
    """Schedules independent reasoning and projects facts into private state."""

    def __init__(
        self,
        world: World,
        agents: list[CharacterAgent],
        director: DirectorAgent,
        memory: MemoryManager | None = None,
        adventures: AdventureManager | None = None,
        systems: CircusSystems | None = None,
        episodes: EpisodeManager | None = None,
        living_world: LivingWorld | None = None,
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
        self.systems = systems or CircusSystems()
        self.episodes = episodes or EpisodeManager(current_day=world.time.day)
        circus_cast = {"pomni", "ragatha", "jax", "gangle", "kinger", "zooble"}
        self.living_world = living_world or LivingWorld(
            world, enabled=circus_cast.issubset(world.characters)
        )
        self.world.living_world = self.living_world
        self.world.events.subscribe(self.systems.observe)
        self.world.events.subscribe(self.episodes.observe)

    async def async_step(self) -> tuple[Event, ...]:
        """Run concurrent mock-AI reasoning, then validate requests in stable order."""
        start = len(self.world.events.history)
        self.world.advance_tick()
        self.episodes.maintain(self.world.time.day, self.world.tick)
        self.systems.advance(self.world.time.day, self.world.time.minute, self.world.tick)
        self._apply_world_pressure()
        self.living_world.advance(self.world)
        await self.director.update_async(self.world)
        decisions = await asyncio.gather(
            *(
                agent.decide_async(
                    self.world.perceive(agent.character_id),
                    self.world.characters[agent.character_id],
                    self.memory.store_for(agent.character_id),
                )
                for agent in self.agents
                if not self.living_world.is_busy(agent.character_id)
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
        accepted_actions: list[Action] = []
        for decision in sorted(decisions, key=lambda item: order[item.action.kind]):
            result = self.world.execute(decision.action)
            if result.accepted:
                accepted_actions.append(decision.action)
        self.living_world.queue_actions(accepted_actions, self.world)
        return self.world.events.history[start:]

    def _apply_world_pressure(self) -> None:
        """Feed shared circus conditions back into private emotional decisions."""
        for character in self.world.characters.values():
            if self.systems.digital_stability < 0.8:
                severity = 0.8 - self.systems.digital_stability
                character.emotions.adjust(anxiety=severity * 0.018, fear=severity * 0.009)
            if self.systems.audience_excitement > 0.78:
                character.emotions.adjust(excitement=(self.systems.audience_excitement - 0.78) * 0.008)
            if self.systems.cast_cohesion < 0.42:
                character.emotions.adjust(loneliness=(0.42 - self.systems.cast_cohesion) * 0.015)

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
        if (
            event.kind is EventKind.ADVENTURE_STARTED
            and event.actor_id is None
            and event.data.get("generated_location_ids")
        ):
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
        self._update_psychology(event)

    def _update_psychology(self, event: Event) -> None:
        """Turn repeated behavior and social consequences into long-lived traits."""
        event_habits = {
            EventKind.MOVED: "move",
            EventKind.SPOKE: "talk",
            EventKind.INSPECTED: "inspect",
            EventKind.RESTED: "rest",
            EventKind.SEARCHED: "search",
            EventKind.EXPLORED: "explore",
            EventKind.HELPED: "help",
            EventKind.LIED: "lie",
        }
        actor = self.world.characters.get(event.actor_id or "")
        if actor and event.kind in event_habits:
            actor.psychology.reinforce_habit(event_habits[event.kind])
        if actor and event.kind is EventKind.HELPED:
            actor.psychology.adjust_standing(status=0.003, reputation=0.006)
        elif actor and event.kind is EventKind.LIED:
            actor.psychology.adjust_standing(status=-0.003, reputation=-0.012)
        elif actor and event.kind is EventKind.ADVENTURE_RESOLVED:
            actor.psychology.adjust_standing(status=0.025, reputation=0.04)

        target_id = event.data.get("target_id")
        target = self.world.characters.get(target_id) if isinstance(target_id, str) else None
        if target and event.kind in {EventKind.SPOKE, EventKind.LIED}:
            target.psychology.beliefs[f"statement:{event.sequence}"] = Belief(
                id=f"statement:{event.sequence}",
                statement=f"{event.actor_id} said: {event.data.get('message', '')}",
                confidence=0.62 if event.kind is EventKind.LIED else 0.84,
                source=f"told_by:{event.actor_id}",
                updated_tick=event.tick,
            )

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
        is_circus = {"pomni", "ragatha", "jax", "gangle", "kinger", "zooble"}.issubset(
            self.world.characters
        )
        return {
            "version": 4,
            "scenario": "digital_circus" if is_circus else "classic_world",
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
            "systems": self.systems.to_dict(),
            "chronicle": self.episodes.to_dict(),
            "director": {
                "name": self.director.name,
                "interval": self.director.interval,
                "once_per_day": self.director.once_per_day,
                "advanced": self.director.advanced,
                "pacing": self.director.pacing.to_dict(),
                "last_intervention_tick": self.director.last_intervention_tick,
                "last_intervention_day": self.director.last_intervention_day,
                "created": self.director._created,
            },
            "adventures_enabled": self.adventures is not None,
            "living_world": self.living_world.to_dict(),
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
                world_theme=str(raw.get("world_theme", "mystery")),
                quest_objective=str(raw.get("quest_objective", "Investigate the world and resolve its central problem.")),
                generated_location_ids=list(raw.get("generated_location_ids", [])),
                objectives=[QuestObjective(**objective) for objective in raw.get("objectives", [])],
                created_day=int(raw.get("created_day", 1)),
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
        is_circus = data.get("scenario") == "digital_circus" or {
            "pomni", "ragatha", "jax", "gangle", "kinger", "zooble"
        }.issubset({character.id for character in characters})
        adventure_manager = (
            AdventureManager(
                random.Random(master_rng.getrandbits(64)),
                CIRCUS_ADVENTURES if is_circus else DEFAULT_ADVENTURES,
            )
            if data.get("adventures_enabled", bool(adventures))
            else None
        )
        raw_director = data.get("director", {})
        director = DirectorAgent(
            random.Random(master_rng.getrandbits(64)),
            interval=int(raw_director.get("interval", 3)),
            situations=CIRCUS_SITUATIONS if is_circus else DEFAULT_SITUATIONS,
            provider=settings.create_provider(),
            timeout_seconds=settings.ai_timeout_seconds,
            adventure_manager=adventure_manager,
            name=str(raw_director.get("name", "Director")),
            once_per_day=bool(raw_director.get("once_per_day", False)),
            advanced=bool(raw_director.get("advanced", False)),
        )
        director.pacing.restore(raw_director.get("pacing", {}))
        director.last_intervention_tick = raw_director.get("last_intervention_tick")
        director.last_intervention_day = raw_director.get("last_intervention_day")
        director._created = int(raw_director.get("created", 0))
        director.last_observed_tick = world.tick
        director.last_generated_event = next(
            (event for event in reversed(world.events.history) if event.actor_id is None),
            None,
        )
        memory = MemoryManager.from_dict(data.get("memory", {}))
        systems = CircusSystems.from_dict(data.get("systems"))
        episodes = EpisodeManager.from_dict(data.get("chronicle"))
        living_world = LivingWorld.from_dict(
            world, data.get("living_world"), enabled=is_circus
        )
        simulation = cls(
            world,
            agents,
            director,
            memory,
            adventure_manager,
            systems=systems,
            episodes=episodes,
            living_world=living_world,
        )
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
            "psychology": {
                "identity": character.psychology.identity,
                "personal_history": list(character.psychology.personal_history),
                "long_term_ambition": character.psychology.long_term_ambition,
                "beliefs": [asdict(belief) for belief in character.psychology.beliefs.values()],
                "internal_conflicts": list(character.psychology.internal_conflicts),
                "social_status": character.psychology.social_status,
                "reputation": character.psychology.reputation,
                "habits": dict(character.psychology.habits),
                "secrets": list(character.psychology.secrets),
            },
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
        psychology_raw = raw.get("psychology", {})
        psychology = CharacterPsychology(
            identity=str(psychology_raw.get("identity", "A resident trying to make sense of the world.")),
            personal_history=tuple(psychology_raw.get("personal_history", [])),
            long_term_ambition=str(psychology_raw.get("long_term_ambition", "Find a meaningful place in the world.")),
            beliefs={
                belief["id"]: Belief(**belief)
                for belief in psychology_raw.get("beliefs", [])
            },
            internal_conflicts=tuple(psychology_raw.get("internal_conflicts", [])),
            social_status=float(psychology_raw.get("social_status", 0.5)),
            reputation=float(psychology_raw.get("reputation", 0.5)),
            habits={str(key): float(value) for key, value in psychology_raw.get("habits", {}).items()},
            secrets=tuple(psychology_raw.get("secrets", [])),
        )
        character = Character(
            raw["id"], raw["name"], raw["location_id"],
            personality=Personality(**raw.get("personality", {})),
            values=tuple(raw.get("values", [])),
            goals=[Goal(**goal) for goal in raw.get("goals", [])],
            fears=tuple(raw.get("fears", [])),
            preferences=tuple(raw.get("preferences", [])),
            psychology=psychology,
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


def create_circus_simulation(
    seed: int | None = None,
    settings: Settings | None = None,
    *,
    enable_adventures: bool = True,
) -> Simulation:
    """Construct the six-character Digital Circus observer world."""
    master_rng = random.Random(seed)
    settings = settings or Settings()
    locations = [
        Location(
            "main_tent", "Main Circus Tent",
            "A vast candy-striped tent filled with three rings, trapezes, lights, and impossible doors.",
            exits={"center_stage", "bedroom_hall", "dining_hall", "backstage", "circus_grounds"},
            features={"three_rings": "Three glowing circus rings rearrange themselves between acts."},
            danger=0.12,
        ),
        Location(
            "center_stage", "Center Stage",
            "A gold-starred performance ring beneath Caine's enormous floating proscenium.",
            exits={"main_tent", "backstage", "portal_gallery"},
            features={"spotlight_console": "Colorful buttons point spotlights at whoever looks most nervous."},
            danger=0.25,
        ),
        Location(
            "bedroom_hall", "Bedroom Hall",
            "A curved hallway of personalized doors, rubbery carpet, portraits, and an EXIT sign that lies.",
            exits={"main_tent"},
            features={"false_exit": "The glowing EXIT door opens onto another section of the same hallway."},
            danger=0.18,
        ),
        Location(
            "dining_hall", "Digital Dining Hall",
            "A banquet room where glossy food respawns and the long table occasionally tells jokes.",
            exits={"main_tent"},
            features={"endless_feast": "Bright cakes and teapots return to their places when nobody watches."},
            danger=0.08,
        ),
        Location(
            "backstage", "Backstage Prop Maze",
            "Curtains divide mountains of toy cannons, hoops, masks, ladders, and unlabeled switches.",
            exits={"main_tent", "center_stage"},
            features={"prop_crates": "The stacked crates are bigger inside than their painted labels suggest."},
            danger=0.38,
        ),
        Location(
            "circus_grounds", "Endless Circus Grounds",
            "A huge outdoor hub surrounds the main tent with winding paths, floating signs, gardens, and distant attractions.",
            exits={"main_tent", "rides_promenade", "digital_lake", "portal_gallery", "grand_theater", "void_overlook"},
            features={"living_map": "A giant map redraws the grounds as Caine adds new attractions."},
            danger=0.1,
        ),
        Location(
            "rides_promenade", "Rides Promenade",
            "A long neon midway holds a carousel, roller coaster, spinning cups, and booths operated by cheerful mannequins.",
            exits={"circus_grounds", "grand_theater"},
            features={"autonomous_carousel": "The carousel chooses its own passengers and destination."},
            danger=0.2,
        ),
        Location(
            "digital_lake", "Digital Lake",
            "A broad reflective lake borders a toy beach, a boathouse, and islands shaped like oversized game pieces.",
            exits={"circus_grounds", "void_overlook"},
            features={"pixel_boathouse": "Colorful boats assemble themselves from cubes at the dock."},
            danger=0.18,
        ),
        Location(
            "portal_gallery", "Adventure Portal Gallery",
            "A vaulted hall contains dozens of dormant doors, each waiting for Caine's next pocket world.",
            exits={"circus_grounds", "center_stage"},
            features={"portal_archive": "Miniature windows replay fragments of completed adventures."},
            danger=0.25,
        ),
        Location(
            "grand_theater", "Grand Digital Theater",
            "An ornate performance hall with impossible balconies, rehearsal rooms, and a stage larger inside than outside.",
            exits={"circus_grounds", "rides_promenade"},
            features={"improv_stage": "The stage generates scenery whenever someone begins a story."},
            danger=0.16,
        ),
        Location(
            "void_overlook", "Void Overlook",
            "A fenced garden terrace looks across the colorful grounds toward the silent edge of the simulation.",
            exits={"circus_grounds", "digital_lake"},
            features={"boundary_glass": "Transparent panels reveal unfinished geometry beyond the safe grounds."},
            danger=0.45,
        ),
        Location(
            "adventure_portal", "Caine's Adventure Portal",
            "A sealed rainbow doorway leading to whichever pocket world Caine has invented today.",
            exits=set(), features={}, danger=0.62,
        ),
        Location(
            "mirror_maze", "Infinite Mirror Maze",
            "A folded gallery of reflections that disagree about who entered first.",
            exits=set(),
            features={"talking_reflections": "The reflections offer contradictory advice in familiar voices."},
            danger=0.48,
        ),
        Location(
            "moon_carnival", "Moonlight Funfair",
            "A pocket carnival beneath a painted moon, filled with memory-powered rides.",
            exits=set(), features={}, danger=0.58,
        ),
        Location(
            "candy_kingdom", "Confection Kingdom",
            "A glossy candy court of peppermint towers and politically ambitious pastries.",
            exits=set(), features={}, danger=0.52,
        ),
    ]

    pomni = Character(
        "pomni", "Pomni", "main_tent",
        personality=Personality(curiosity=.62, bravery=.36, risk_tolerance=.28, empathy=.68, honesty=.82, sociability=.38, independence=.72, impulsiveness=.35),
        values=("freedom", "truth", "identity"),
        goals=[Goal("exit", "Find a real way out of the circus", .98, ("discover", "explore")), Goal("stay_sane", "Understand the rules before they change", .8, ("discover",))],
        fears=("abstraction", "being trapped"), preferences=("clear answers", "quiet corners"),
        emotions=EmotionalState(happiness=.18, fear=.58, curiosity=.64, anxiety=.78, excitement=.2),
    )
    ragatha = Character(
        "ragatha", "Ragatha", "bedroom_hall",
        personality=Personality(curiosity=.58, bravery=.62, risk_tolerance=.48, empathy=.96, honesty=.88, patience=.84, sociability=.88, loyalty=.92),
        values=("kindness", "friendship", "hope"),
        goals=[Goal("support", "Keep everyone together and feeling safe", .95, ("protect", "social"), "pomni"), Goal("hope", "Find something good in today's adventure", .72, ("discover",))],
        fears=("friends abstracting",), preferences=("helping", "conversation"),
    )
    jax = Character(
        "jax", "Jax", "center_stage",
        personality=Personality(curiosity=.7, bravery=.82, risk_tolerance=.9, empathy=.15, honesty=.18, patience=.18, sociability=.8, independence=.88, competitiveness=.93, impulsiveness=.86),
        values=("amusement", "freedom", "winning"),
        goals=[Goal("chaos", "Make today's adventure entertaining", .94, ("explore", "resource")), Goal("win", "Be first to claim the best prize", .84, ("discover", "resource"))],
        fears=("boredom",), preferences=("pranks", "dangerous shortcuts"),
    )
    gangle = Character(
        "gangle", "Gangle", "backstage",
        personality=Personality(curiosity=.52, bravery=.25, risk_tolerance=.2, empathy=.8, honesty=.87, patience=.72, sociability=.35, loyalty=.66),
        values=("creativity", "acceptance", "friendship"),
        goals=[Goal("create", "Find something inspiring among the circus props", .78, ("discover",)), Goal("belong", "Take part without losing another mask", .82, ("social", "protect"))],
        fears=("broken masks", "ridicule"), preferences=("drawing", "gentle company"),
        emotions=EmotionalState(happiness=.28, fear=.38, curiosity=.48, anxiety=.52, loneliness=.34),
    )
    kinger = Character(
        "kinger", "Kinger", "dining_hall",
        personality=Personality(curiosity=.76, bravery=.43, risk_tolerance=.42, empathy=.7, honesty=.78, patience=.48, sociability=.42, independence=.5, impulsiveness=.54),
        values=("memory", "companionship", "insects"),
        goals=[Goal("remember", "Recover useful fragments of forgotten knowledge", .86, ("discover",)), Goal("protect", "Protect the others when clarity returns", .7, ("protect", "social"))],
        fears=("the dark becoming quiet",), preferences=("pillow forts", "insect collections"),
        emotions=EmotionalState(happiness=.38, fear=.42, curiosity=.76, anxiety=.46, excitement=.44),
    )
    zooble = Character(
        "zooble", "Zooble", "main_tent",
        personality=Personality(curiosity=.45, bravery=.68, risk_tolerance=.6, empathy=.52, honesty=.76, patience=.22, sociability=.2, independence=.97, competitiveness=.45),
        values=("autonomy", "honesty", "self-expression"),
        goals=[Goal("autonomy", "Avoid being pushed into Caine's nonsense", .9, ()), Goal("pieces", "Find parts that finally feel right", .74, ("resource", "discover"))],
        fears=("losing control",), preferences=("personal space", "direct answers"),
    )
    characters = [pomni, ragatha, jax, gangle, kinger, zooble]
    pomni.psychology = CharacterPsychology(
        identity="A cautious newcomer who tests every rule while trying to remain herself.",
        personal_history=("Arrived in the circus with no reliable memory of the outside.", "Learned that obvious exits cannot be trusted."),
        long_term_ambition="Discover whether freedom is possible without losing herself or the others.",
        beliefs={
            "exit": Belief("exit", "A real exit may exist, but it will not look like Caine's signs.", .71),
            "group": Belief("group", "Survival is safer with allies even when closeness feels risky.", .66),
        },
        internal_conflicts=("Desperately wants answers but fears what investigation may reveal.",),
        social_status=.42, reputation=.58, habits={"inspect": .62, "search": .56},
        secrets=("She sometimes doubts whether memories of the outside are truly hers.",),
    )
    ragatha.psychology = CharacterPsychology(
        identity="The group's emotional anchor, choosing kindness as an act of resilience.",
        personal_history=("Has welcomed several frightened arrivals.", "Has repeatedly held the group together after dangerous adventures."),
        long_term_ambition="Build enough trust that nobody has to face the circus alone.",
        beliefs={"kindness": Belief("kindness", "Consistent care can keep people grounded.", .91)},
        internal_conflicts=("Hides her own fear to protect everyone else's hope.",),
        social_status=.72, reputation=.84, habits={"help": .78, "talk": .66},
        secrets=("Her optimism sometimes feels like a role she cannot stop performing.",),
    )
    jax.psychology = CharacterPsychology(
        identity="A confident provocateur who treats the circus as a game he intends to win.",
        personal_history=("Learned that jokes keep others at a useful distance.", "Usually finds the dangerous shortcut first."),
        long_term_ambition="Stay impossible to control and never let the circus become boring.",
        beliefs={"rules": Belief("rules", "Rules are props for whoever is bold enough to move them.", .9)},
        internal_conflicts=("Craves an audience but resists genuine dependence on anyone.",),
        social_status=.68, reputation=.34, habits={"explore": .72, "lie": .64, "move": .6},
        secrets=("Being ignored unsettles him more than any dangerous adventure.",),
    )
    gangle.psychology = CharacterPsychology(
        identity="A sensitive artist whose masks make private feelings visible.",
        personal_history=("Has rebuilt fragile masks from backstage scraps.", "Found that creativity survives even the circus's worst jokes."),
        long_term_ambition="Create something honest enough to be valued without needing a mask.",
        beliefs={"art": Belief("art", "Making things can preserve feelings the circus tries to flatten.", .88)},
        internal_conflicts=("Wants to be seen while fearing that attention will turn cruel.",),
        social_status=.38, reputation=.63, habits={"inspect": .54, "rest": .38},
        secrets=("Keeps sketches of every friend in case the circus changes them.",),
    )
    kinger.psychology = CharacterPsychology(
        identity="A scattered elder whose flashes of clarity carry hard-earned courage.",
        personal_history=("Has survived longer in the circus than his memory can organize.", "Remembers important truths most clearly in darkness."),
        long_term_ambition="Recover enough of the past to protect the cast from repeating it.",
        beliefs={"dark": Belief("dark", "Quiet darkness makes buried memories easier to reach.", .79)},
        internal_conflicts=("His insight is strongest when his confidence is least reliable.",),
        social_status=.56, reputation=.69, habits={"search": .65, "inspect": .58},
        secrets=("He remembers fragments of someone the others no longer mention.",),
    )
    zooble.psychology = CharacterPsychology(
        identity="An independent modular person who refuses to let others define the right arrangement.",
        personal_history=("Has tried countless combinations of replacement parts.", "Learned to distrust mandatory enthusiasm."),
        long_term_ambition="Claim complete authority over their body, time, and participation.",
        beliefs={"choice": Belief("choice", "Consent matters even when the whole world is artificial.", .96)},
        internal_conflicts=("Wants distance from the chaos but still notices when the group needs help.",),
        social_status=.51, reputation=.61, habits={"rest": .46, "move": .34},
        secrets=("They keep one disliked old piece because it is tied to a rare good memory.",),
    )
    ragatha.relationships["pomni"] = Relationship(trust=.82, friendship=.8, loyalty=.86, affection=.78)
    pomni.relationships["ragatha"] = Relationship(trust=.74, friendship=.6)
    jax.relationships["gangle"] = Relationship(trust=.28, friendship=.34, respect=.42, suspicion=.3)
    gangle.relationships["jax"] = Relationship(trust=.2, friendship=.25, suspicion=.58, fear=.35)
    kinger.relationships["ragatha"] = Relationship(trust=.76, friendship=.7, respect=.72)
    zooble.relationships["jax"] = Relationship(trust=.32, friendship=.3, suspicion=.5)

    objects = [
        WorldObject("rubber_chicken", "a rubber chicken", "It recites legal disclaimers when squeezed.", "backstage", portable=True, tags={"toy"}),
        WorldObject("comedy_mask", "a spare comedy mask", "The porcelain smile changes when viewed from the side.", "bedroom_hall", portable=True, tags={"mask", "mystery"}),
        WorldObject("exit_key", "a pixel key", "A flickering key labelled EXIT, probably dishonestly.", "main_tent", portable=True, hidden=True, tags={"mystery", "valuable"}),
        WorldObject("digital_cake", "an immaculate digital cake", "Every slice grows back with different frosting.", "dining_hall", portable=False, tags={"food"}, uses_remaining=99),
    ]
    world = World(locations, characters, objects=objects)
    agents = [
        CharacterAgent(
            character.id,
            AgentTendencies(curiosity=character.personality.curiosity, sociability=character.personality.sociability),
            random.Random(master_rng.getrandbits(64)),
            provider=settings.create_provider(), timeout_seconds=settings.ai_timeout_seconds,
        )
        for character in characters
    ]
    adventure_manager = (
        AdventureManager(random.Random(master_rng.getrandbits(64)), CIRCUS_ADVENTURES)
        if enable_adventures else None
    )
    director = DirectorAgent(
        random.Random(master_rng.getrandbits(64)), situations=CIRCUS_SITUATIONS,
        provider=settings.create_provider(), timeout_seconds=settings.ai_timeout_seconds,
        adventure_manager=adventure_manager, name="Caine", once_per_day=True,
        advanced=True,
    )
    return Simulation(world, agents, director, adventures=adventure_manager)
