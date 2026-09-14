"""Independent character brains with mock-AI structured decision selection."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field

from autonomous_ai_world.ai import AIProvider, MockAIProvider
from autonomous_ai_world.memory import Memory, MemoryStore
from autonomous_ai_world.models import (
    Action,
    ActionKind,
    Character,
    Decision,
    EventKind,
    Goal,
    Intention,
    Perception,
    Personality,
    Relationship,
    Weather,
)
from autonomous_ai_world.tools import StructuredOutputError, decision_payload, parse_decision


@dataclass(frozen=True, slots=True)
class AgentTendencies:
    """Backwards-compatible Stage 1 profile used by direct policy tests."""

    curiosity: float = 0.5
    sociability: float = 0.5
    rest_threshold: int = 2
    remarks: tuple[str, ...] = (
        "Something about this place has my attention.",
        "What do you make of all this?",
        "I wonder what we will find next.",
    )


@dataclass(slots=True)
class CharacterAgent:
    """Reasons over one character's local context and emits validated requests."""

    character_id: str
    tendencies: AgentTendencies
    rng: random.Random
    provider: AIProvider = field(default_factory=MockAIProvider)
    timeout_seconds: float = 2.0
    _inspected: set[tuple[str, str]] = field(default_factory=set)
    last_provider_error: str | None = None
    last_retrieved_memories: tuple[Memory, ...] = ()

    def decide(self, perception: Perception) -> Action:
        """Synchronous local policy retained for simple embedding and Stage 1 callers."""
        character = Character(
            self.character_id,
            self.character_id.title(),
            perception.location_id,
            personality=Personality(
                curiosity=self.tendencies.curiosity,
                sociability=self.tendencies.sociability,
            ),
            goals=[Goal("explore", "Explore the world", 0.6, ("explore",))],
        )
        character.energy = perception.energy
        action = self._candidate_decisions(perception, character, ())[0][0].action
        self._record_inspection(perception, action)
        return action

    async def decide_async(
        self,
        perception: Perception,
        character: Character,
        memory_store: MemoryStore,
    ) -> Decision:
        query = " ".join(
            [goal.description for goal in character.goals]
            + [character.psychology.long_term_ambition]
            + [belief.statement for belief in character.psychology.beliefs.values()]
            + [event.summary for event in perception.recent_events[-4:]]
        )
        memories = memory_store.retrieve(
            query,
            perception.tick,
            participants=perception.nearby_characters,
            limit=5,
        )
        self.last_retrieved_memories = memories
        character.retrieved_memory_ids = [memory.id for memory in memories]
        candidates = self._candidate_decisions(perception, character, memories)
        fallback = candidates[0][0]
        context = {
            "character": self._character_context(character),
            "perception": self._perception_context(perception),
            "relevant_memories": [memory.content for memory in memories],
            "candidates": [decision_payload(decision, score) for decision, score in candidates],
        }
        try:
            raw = await asyncio.wait_for(
                self.provider.generate_structured("character_decision", context),
                timeout=self.timeout_seconds,
            )
            decision = parse_decision(raw, self.character_id)
            allowed = {
                (candidate.action.kind, candidate.action.target_id)
                for candidate, _ in candidates
            }
            if (decision.action.kind, decision.action.target_id) not in allowed:
                raise StructuredOutputError("provider selected an unavailable action")
            self.last_provider_error = None
        except Exception as exc:
            # The broad final catch protects simulation consistency from provider adapters.
            self.last_provider_error = f"{type(exc).__name__}: {exc}"
            decision = fallback
        character.current_intention = Intention(
            decision.intent,
            decision.action.kind,
            decision.action.target_id,
            decision.priority,
            decision.reason,
        )
        self._record_inspection(perception, decision.action)
        return decision

    def _candidate_decisions(
        self,
        perception: Perception,
        character: Character,
        memories: tuple[Memory, ...],
    ) -> list[tuple[Decision, float]]:
        p = character.personality
        goal_scores = self._goal_scores(character.goals)
        memory_text = " ".join(memory.content.lower() for memory in memories)
        recent_social_count = sum(
            event.actor_id == character.id
            and event.kind in {EventKind.SPOKE, EventKind.HELPED, EventKind.LIED}
            for event in perception.recent_events[-6:]
        )
        social_saturation = recent_social_count * 0.18
        candidates: list[tuple[Decision, float]] = []

        def add(
            kind: ActionKind,
            score: float,
            intent: str,
            reason: str,
            target: str | None = None,
            message: str | None = None,
        ) -> None:
            # Repeated choices become habits without ever overriding safety validation.
            score += character.psychology.habits.get(kind.value, 0.0) * 0.24
            if (
                character.last_action
                and character.last_action.kind is kind
                and character.last_action.target_id == target
            ):
                score -= 0.35
            jitter = self.rng.random() * (0.08 + p.impulsiveness * 0.12)
            priority = max(0.0, min(1.0, score))
            candidates.append(
                (
                    Decision(
                        intent,
                        Action(character.id, kind, target_id=target, message=message),
                        priority,
                        reason,
                    ),
                    score + jitter,
                )
            )

        if perception.energy <= self.tendencies.rest_threshold:
            kind = ActionKind.SLEEP if perception.is_night else ActionKind.REST
            add(kind, 2.0, "recover_energy", "Low energy overrides less urgent goals.")
            return candidates

        recent_situations = {
            event.data.get("feature_id")
            for event in perception.recent_events
            if event.kind
            in {
                EventKind.SITUATION_CREATED,
                EventKind.ADVENTURE_STARTED,
                EventKind.ADVENTURE_PROGRESSED,
            }
        }
        adventure_phases = {
            item["phase"] for item in perception.active_adventures
        }
        unseen_features = [
            feature_id
            for feature_id in sorted(perception.features)
            if (perception.location_id, feature_id) not in self._inspected
        ]
        for feature_id in unseen_features:
            prompted = feature_id in recent_situations
            score = 0.4 + p.curiosity * 0.75 + goal_scores["discover"] * 0.45
            score += 0.5 if prompted else 0.0
            if any(adventure.get("objective_target_id") == feature_id for adventure in perception.active_adventures):
                score += 1.0
            if any(adventure.get('story_target_id') == feature_id for adventure in perception.active_adventures):
                score += 4.0
            score -= character.emotions.fear * (0.2 + perception.location_danger)
            add(
                ActionKind.INSPECT,
                score,
                "investigate_feature",
                "Curiosity and discovery goals favor examining an unknown feature.",
                feature_id,
            )

        for object_id in sorted(perception.visible_objects):
            score = 0.35 + p.curiosity * 0.4 + goal_scores["resource"] * 0.6
            add(
                ActionKind.PICK_UP,
                score,
                "acquire_object",
                "A visible object may support personal goals.",
                object_id,
            )

        for object_id, tags in perception.inventory_tags.items():
            if (
                "food" in tags
                and perception.hunger >= 15
                and perception.inventory_uses.get(object_id) != 0
            ):
                add(
                    ActionKind.USE_ITEM,
                    0.45 + perception.hunger / 100,
                    "satisfy_hunger",
                    "Hunger makes using an available food item worthwhile.",
                    object_id,
                )

        social_memory = 0.15 if "helps" in memory_text or "helped" in memory_text else 0.0
        for target_id in perception.nearby_characters:
            relation = character.relationships.get(target_id, Relationship())
            talk_score = (
                0.25
                + p.sociability * 0.65
                + relation.friendship * 0.25
                + relation.trust * 0.15
                + goal_scores["social"] * 0.4
                + social_memory
                - relation.anger * 0.3
                - social_saturation
                + character.psychology.social_status * 0.08
            )
            add(
                ActionKind.TALK,
                talk_score,
                "connect_with_character",
                "Sociability, goals, memories, and relationship state favor conversation.",
                target_id,
                self._dialogue_line(character, target_id, perception),
            )
            if perception.nearby_energy.get(target_id, 10) < 5:
                help_score = (
                    0.4
                    + p.empathy * 0.65
                    + p.loyalty * relation.friendship * 0.4
                    + goal_scores["protect"] * 0.55
                    + social_memory
                    + character.psychology.reputation * 0.12
                    - social_saturation
                )
                add(
                    ActionKind.HELP,
                    help_score,
                    "help_character",
                    "Empathy, loyalty, and a protection goal favor helping someone tired.",
                    target_id,
                )
            lie_score = (
                (1.0 - p.honesty) * 0.65
                + p.competitiveness * 0.25
                + relation.suspicion * 0.15
                - relation.friendship * 0.3
                + (1.0 - character.psychology.reputation) * 0.1
                - social_saturation
            )
            if lie_score > 0.55:
                add(
                    ActionKind.LIE,
                    lie_score,
                    "mislead_character",
                    "Low honesty and competitive pressure make deception plausible.",
                    target_id,
                    self._deception_line(character, perception),
                )

        danger_memory = "danger" in memory_text or "storm" in memory_text
        for destination in perception.exits:
            quest_move = any(
                adventure.get("generated_world") == "yes"
                and adventure.get("next_location_id") == destination
                for adventure in perception.active_adventures
            )
            known_danger = any(
                destination in fact.content.lower() and "danger" in fact.content.lower()
                for fact in perception.known_facts
            )
            danger_penalty = (1.0 - p.risk_tolerance) * (
                0.65 if known_danger or danger_memory else 0.15
            )
            move_score = (
                0.32
                + p.curiosity * 0.35
                + p.risk_tolerance * 0.25
                + goal_scores["explore"] * 0.5
                - character.emotions.fear * 0.4
                - danger_penalty
            )
            for adventure in perception.active_adventures:
                if (
                    adventure["phase"] == "discovery"
                    and adventure["hidden_location_id"] == destination
                ):
                    move_score += 0.45 + (p.curiosity + p.bravery) * 0.25
                if adventure.get("generated_world") == "yes" and adventure.get("next_location_id") == destination:
                    move_score += 0.72 + p.bravery * 0.18
                    if adventure.get('story_location_id'):
                        move_score += 2.0
            if perception.homeward_exit_id == destination:
                move_score += 0.9
            add(
                ActionKind.MOVE,
                move_score,
                "return_to_circus" if perception.homeward_exit_id == destination else "advance_quest" if quest_move else "travel_toward_goal",
                "The completed quest makes returning through the portal the next priority."
                if perception.homeward_exit_id == destination
                else "The active objective identifies this as the next useful part of Caine's world."
                if quest_move
                else "Exploration goals are balanced against known danger and fear.",
                destination,
            )

        add(
            ActionKind.SEARCH,
            0.25
            + p.curiosity * 0.45
            + goal_scores["discover"] * 0.5
            + (0.65 if "investigation" in adventure_phases else 0.0),
            "search_area",
            "Searching may reveal information not visible at first glance.",
        )
        add(
            ActionKind.EXPLORE,
            0.25 + p.curiosity * 0.4 + goal_scores["explore"] * 0.45,
            "explore_location",
            "General exploration advances curiosity and exploration goals.",
        )
        add(ActionKind.REST, 0.15 + (10 - perception.energy) * 0.05, "pause", "Rest preserves energy.")
        candidates.sort(key=lambda item: item[1], reverse=True)
        return candidates

    @staticmethod
    def _dialogue_line(character: Character, target_id: str, perception: Perception) -> str:
        adventure = perception.active_adventures[0] if perception.active_adventures else None
        if adventure:
            topic = f"{adventure['title']}; our objective is to {str(adventure.get('quest_objective', 'finish the objective')).lower()}"
        elif interesting := next(
            (
                event for event in reversed(perception.recent_events)
                if event.kind in {
                    EventKind.ADVENTURE_STARTED, EventKind.ADVENTURE_PROGRESSED,
                    EventKind.ADVENTURE_RESOLVED, EventKind.OBJECT_DISCOVERED,
                    EventKind.SITUATION_CREATED, EventKind.ENVIRONMENT_CHANGED,
                }
            ),
            None,
        ):
            topic = interesting.summary.rstrip(".")
        elif perception.features:
            topic = next(iter(perception.features.values())).rstrip(".")
        else:
            topic = f"what is happening in {perception.location_name}"
        openers = {
            "pomni": ("Wait, {target}.", "Okay, {target}, listen.", "Does this seem wrong to you, {target}?", "I need a second opinion, {target}."),
            "ragatha": ("Stay close, {target}.", "How are you holding up, {target}?", "We can work this out, {target}.", "I have your back, {target}."),
            "jax": ("Hey, {target}.", "Try to keep up, {target}.", "This might finally be entertaining, {target}.", "Good news, {target}: I have an idea."),
            "gangle": ("Um, {target}?", "I have an idea, {target}.", "Maybe this could work, {target}.", "Can I show you something, {target}?"),
            "kinger": ("{target}! I remembered something!", "The pattern is back, {target}.", "Listen carefully, {target}.", "This is almost familiar, {target}."),
            "zooble": ("{target}, I am only saying this once.", "Let's be direct, {target}.", "I have a practical suggestion, {target}.", "Before Caine complicates this, {target}."),
        }
        observations = (
            "We should verify {topic} before choosing a route.",
            "The safest useful move is to compare what we know about {topic}.",
            "Something in this place keeps pointing back to {topic}.",
            "Let's split the problem into one step: {topic}.",
            "I do not think Caine explained everything about {topic}.",
            "We should decide who handles the risky part of {topic}.",
            "There may be a shortcut, but first we need to understand {topic}.",
            "Our last attempt changes how I see {topic}.",
        )
        dominant = max(
            character.emotions.__dataclass_fields__,
            key=lambda name: getattr(character.emotions, name),
        )
        closers = {
            "fear": ("I really do not want us getting separated.", "Keep the portal in sight.", "Tell me if the world changes again."),
            "anxiety": ("One careful step at a time.", "Let's leave ourselves a way back.", "I would rather have an actual plan."),
            "anger": ("I am done letting the rules push us around.", "This time we push back.", "I want a straight answer."),
            "happiness": ("This might actually work.", "We are doing better than I expected.", "At least we are making progress."),
            "curiosity": ("I want to see what happens next.", "There is definitely more to discover.", "The details do not quite match."),
            "excitement": ("Let's move before the opportunity disappears.", "This is the interesting part.", "I am ready to try it."),
            "loneliness": ("Just do not leave me behind.", "It is easier if we stay together.", "I could use some company on this one."),
        }
        seed = perception.tick + sum(ord(letter) for letter in f"{character.id}:{target_id}:{perception.location_id}")
        voice_options = openers.get(character.id, ("Can we talk, {target}?",))
        opener = voice_options[seed % len(voice_options)].format(target=target_id.title())
        short_topic = topic if len(topic) <= 115 else f"{topic[:112].rsplit(' ', 1)[0]}…"
        observation = observations[(seed // 3) % len(observations)].format(topic=short_topic)
        coda_options = closers[dominant]
        coda = coda_options[(seed // 7) % len(coda_options)]
        if perception.energy <= 3:
            coda = "I can help, but I need a breather soon."
        return f"{opener} {observation} {coda}"

    @staticmethod
    def _deception_line(character: Character, perception: Perception) -> str:
        if perception.active_adventures:
            title = perception.active_adventures[0]["title"]
            return f"Caine told me the safest route through {title}; it definitely goes the other way."
        visible = next(iter(perception.visible_objects.values()), None)
        if visible:
            return f"That thing over there is completely useless. I already checked."
        return f"Nothing unusual happened in {perception.location_name}. Trust me."

    def _record_inspection(self, perception: Perception, action: Action) -> None:
        if action.kind is ActionKind.INSPECT and action.target_id:
            self._inspected.add((perception.location_id, action.target_id))

    @staticmethod
    def _goal_scores(goals: list[Goal]) -> dict[str, float]:
        result = {"explore": 0.0, "discover": 0.0, "social": 0.0, "protect": 0.0, "resource": 0.0}
        for goal in goals:
            for tag in goal.tags:
                if tag in result:
                    result[tag] = max(result[tag], goal.priority)
        return result

    @staticmethod
    def _character_context(character: Character) -> dict[str, object]:
        return {
            "id": character.id,
            "personality": {
                name: getattr(character.personality, name)
                for name in character.personality.__dataclass_fields__
            },
            "goals": [goal.description for goal in character.goals],
            "identity": character.psychology.identity,
            "personal_history": list(character.psychology.personal_history),
            "long_term_ambition": character.psychology.long_term_ambition,
            "beliefs": [
                {"statement": belief.statement, "confidence": belief.confidence}
                for belief in character.psychology.beliefs.values()
            ],
            "internal_conflicts": list(character.psychology.internal_conflicts),
            "social_status": character.psychology.social_status,
            "reputation": character.psychology.reputation,
            "habits": dict(character.psychology.habits),
            "secrets": list(character.psychology.secrets),
            "emotions": {
                name: getattr(character.emotions, name)
                for name in character.emotions.__dataclass_fields__
            },
        }

    @staticmethod
    def _perception_context(perception: Perception) -> dict[str, object]:
        return {
            "time": perception.time_label,
            "weather": perception.weather.value,
            "location": perception.location_id,
            "exits": list(perception.exits),
            "nearby_characters": list(perception.nearby_characters),
            "visible_objects": list(perception.visible_objects),
            "inventory": list(perception.inventory),
            "energy": perception.energy,
            "hunger": perception.hunger,
            "active_adventures": [dict(item) for item in perception.active_adventures],
            "is_pocket_world": perception.is_pocket_world,
            "homeward_exit_id": perception.homeward_exit_id,
            "current_activity": perception.current_activity,
            "activity_phase": perception.activity_phase,
            "available_activity_spots": list(perception.available_activity_spots),
            "nearby_distances": dict(perception.nearby_distances),
        }
