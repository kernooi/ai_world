"""Data-driven Stage 8 adventure seeding and event-driven phase progression."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Any, Mapping

from autonomous_ai_world.ai import AIProvider
from autonomous_ai_world.models import (
    Adventure,
    AdventurePhase,
    AdventureStatus,
    Event,
    EventKind,
)
from autonomous_ai_world.world import World


@dataclass(frozen=True, slots=True)
class PocketZoneTemplate:
    slug: str
    name: str
    description: str
    danger: float
    features: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class AdventureTemplate:
    id: str
    title: str
    premise: str
    mystery: str
    stakes: str
    hook_name: str
    hook_description: str
    clue_name: str
    clue_description: str
    hidden_location_id: str
    escalation_name: str
    escalation_description: str
    world_theme: str = "mystery"
    quest_objective: str = "Reach the heart of the world and resolve its central problem."
    zones: tuple[PocketZoneTemplate, ...] = ()


DEFAULT_ADVENTURES = (
    AdventureTemplate(
        id="echo_below",
        title="The Echo Below",
        premise="A repeating signal seems to answer the residents' movements.",
        mystery="What is producing the signal, and why has it begun responding now?",
        stakes="The signal is growing stronger and may destabilize its hidden source.",
        hook_name="responsive_signal",
        hook_description=(
            "A soft sequence of tones repeats nearby, changing whenever someone moves."
        ),
        clue_name="a resonant compass shard",
        clue_description=(
            "The metal shard vibrates in time with the signal and points toward a sealed path."
        ),
        hidden_location_id="observatory",
        escalation_name="unstable_signal_core",
        escalation_description=(
            "A suspended ring of metal and light pulses faster as anyone approaches it."
        ),
    ),
)

CIRCUS_ADVENTURES = (
    AdventureTemplate(
        id="glitching_midway",
        title="The Glitching Midway",
        premise="Caine unveils a cheerful midway game whose prizes have begun rewriting the tent.",
        mystery="Which impossible prize is causing the glitch, and what does it want the cast to play?",
        stakes="If the game keeps spreading, every room may be folded into an endless obstacle course.",
        hook_name="laughing_scoreboard",
        hook_description=(
            "A neon scoreboard laughs, changes its own rules, and awards points for things nobody did."
        ),
        clue_name="a pixelated golden ticket",
        clue_description=(
            "The ticket flickers between destinations and points toward Caine's sealed adventure portal."
        ),
        hidden_location_id="adventure_portal",
        escalation_name="impossible_prize_wheel",
        escalation_description=(
            "A towering prize wheel spins through symbols that do not fit inside ordinary geometry."
        ),
        world_theme="glitch_midway",
        quest_objective="Win three impossible midway games and shut down the rule-breaking prize wheel.",
        zones=(
            PocketZoneTemplate("ticket_plaza", "Glitched Ticket Plaza", "Striped booths repeat into the horizon while scoreboards rewrite the rules.", .32, (("ring_toss", "A ring toss changes the target after every throw."),)),
            PocketZoneTemplate("prize_canyons", "Prize Canyons", "Mountains of plush prizes form bright canyons patrolled by wind-up judges.", .48, (("plush_bridge", "A bridge made of prizes rearranges when anyone celebrates."),)),
            PocketZoneTemplate("wheel_arena", "Impossible Wheel Arena", "A colossal prize wheel bends the midway around its flashing center.", .67),
        ),
    ),
    AdventureTemplate(
        id="moonlight_funfair",
        title="The Moonlight Funfair",
        premise="Caine opens a midnight carnival where every ride is powered by a missing memory.",
        mystery="Why does the carousel know details the cast can no longer remember?",
        stakes="The funfair may keep the memories permanently if its final ride completes a circuit.",
        hook_name="remembering_carousel",
        hook_description="A tiny carousel hums a melody that each character recognizes differently.",
        clue_name="a moon-stamped ride token",
        clue_description="The silver token projects a route through an unopened lunar doorway.",
        hidden_location_id="moon_carnival",
        escalation_name="memory_ferris_wheel",
        escalation_description="A vast wheel turns overhead, displaying stolen memories in its carriages.",
        world_theme="moon_funfair",
        quest_objective="Recover the stolen memory lights and stop the ferris wheel before dawn.",
        zones=(
            PocketZoneTemplate("lunar_gate", "Lunar Turnstiles", "Silver turnstiles float above a carnival road beneath a painted moon.", .3),
            PocketZoneTemplate("carousel_fields", "Remembering Carousel Fields", "Dozens of riderless carousels whisper mismatched memories.", .46, (("memory_lanterns", "Loose memories glow inside paper lanterns."),)),
            PocketZoneTemplate("ferris_crown", "Ferris Crown", "The memory-powered wheel rises above a sea of midnight clouds.", .7),
        ),
    ),
    AdventureTemplate(
        id="confection_kingdom",
        title="The Confection Kingdom Coup",
        premise="Caine declares the cast diplomatic envoys to a dessert kingdom in the middle of a coup.",
        mystery="Who replaced the candy crown, and why is the new one whispering orders?",
        stakes="The unstable kingdom will melt into the circus and trap the cast in an endless banquet.",
        hook_name="royal_sugar_summons",
        hook_description="A frosting-sealed invitation demands six envoys and refuses to be discarded.",
        clue_name="a crystallized crown fragment",
        clue_description="The sugar crystal points toward a peppermint door hidden beyond the tent.",
        hidden_location_id="candy_kingdom",
        escalation_name="whispering_candy_crown",
        escalation_description="The false crown grows new jeweled eyes whenever someone obeys it.",
        world_theme="candy_kingdom",
        quest_objective="Identify the false candy crown and restore the kingdom without letting it melt.",
        zones=(
            PocketZoneTemplate("sugar_road", "Sugar Road", "A sparkling road winds through gumdrop orchards toward peppermint walls.", .28),
            PocketZoneTemplate("fondant_city", "Fondant City", "Icing citizens debate beneath wafer towers and caramel banners.", .42, (("candy_council", "The candy council accuses everyone in equal measure."),)),
            PocketZoneTemplate("crown_court", "Crown Court", "A glossy throne room slowly warms beneath an artificial sun.", .64),
        ),
    ),
    AdventureTemplate(
        id="clockwork_cloud",
        title="The Clockwork Cloud Heist",
        premise="Caine sends the cast to a sky factory where tomorrow's weather has been stolen.",
        mystery="Who locked the storm engine, and why are the clouds counting backward?",
        stakes="The factory will drop a permanent thunderstorm onto the circus grounds.",
        hook_name="brass_weather_vane",
        hook_description="A brass weather vane points upward and prints tickets to a city in the clouds.",
        clue_name="a compressed thunder key",
        clue_description="The key rumbles in a glass capsule and projects a route through the portal.",
        hidden_location_id="adventure_portal",
        escalation_name="reverse_storm_engine",
        escalation_description="A giant engine winds lightning backward through hundreds of ticking gears.",
        world_theme="clockwork_sky",
        quest_objective="Recover the forecast gears and restart the storm engine in the correct direction.",
        zones=(
            PocketZoneTemplate("cloud_docks", "Cloud Docks", "Airships unload bottled breezes beside brass platforms suspended in open sky.", .34),
            PocketZoneTemplate("forecast_factory", "Forecast Factory", "Conveyor belts carry rain, sunlight, and hail through rooms of turning gears.", .52, (("weather_ledger", "A ledger lists tomorrow's weather as missing inventory."),)),
            PocketZoneTemplate("storm_spire", "Storm Spire", "Lightning coils around a tower whose clock faces count backward.", .74),
        ),
    ),
    AdventureTemplate(
        id="storybook_sea",
        title="The Storybook Sea Rescue",
        premise="An unfinished story ocean is erasing every island before its ending can be written.",
        mystery="Which character tore out the final page?",
        stakes="Without an ending, the sea will pour through the portal and dissolve the circus floor.",
        hook_name="talking_storybook",
        hook_description="A soaked storybook begs the cast to rescue an island that vanishes sentence by sentence.",
        clue_name="a waterproof comma",
        clue_description="The punctuation mark acts like a compass whenever the next chapter is nearby.",
        hidden_location_id="adventure_portal",
        escalation_name="unfinished_ending",
        escalation_description="A blank final page hangs over the ocean and pulls the world into its margins.",
        world_theme="storybook_sea",
        quest_objective="Find the missing final page and choose an ending that saves the islands.",
        zones=(
            PocketZoneTemplate("paper_harbor", "Paper Harbor", "Folded ships bob on ink-blue water beside cardboard docks.", .3),
            PocketZoneTemplate("chapter_islands", "Chapter Islands", "Each island follows a different story genre and disappears at its final sentence.", .5, (("narrator_shell", "A seashell narrates choices a few seconds before they happen."),)),
            PocketZoneTemplate("margin_maelstrom", "Margin Maelstrom", "Torn paragraphs spiral around a blank page at the edge of the sea.", .72),
        ),
    ),
    AdventureTemplate(
        id="neon_noodle_city",
        title="The Neon Noodle Delivery",
        premise="Caine declares the cast express couriers in a vertical city whose streets keep changing floors.",
        mystery="Why does every delivery address belong to the same unknown customer?",
        stakes="Late deliveries feed a transit glitch that could strand the cast between city layers.",
        hook_name="singing_delivery_box",
        hook_description="A hot delivery box sings directions that contradict its flashing address label.",
        clue_name="an elevator-flavored transit card",
        clue_description="The card opens a portal shaped like a crowded subway door.",
        hidden_location_id="adventure_portal",
        escalation_name="hungry_transit_core",
        escalation_description="A neon routing engine consumes street signs and demands one final impossible delivery.",
        world_theme="neon_city",
        quest_objective="Complete the impossible delivery route and expose the customer controlling the city.",
        zones=(
            PocketZoneTemplate("noodle_station", "Noodle Station", "Steam-powered trains weave between glowing food stalls and floating signs.", .33),
            PocketZoneTemplate("vertical_market", "Vertical Market", "Shops cling to every side of a tower while elevators travel sideways.", .49, (("address_swarm", "A flock of animated address labels points in competing directions."),)),
            PocketZoneTemplate("routing_rooftop", "Routing Rooftop", "A pulsing map engine redraws the entire skyline beneath a neon moon.", .69),
        ),
    ),
)


class AdventureManager:
    """Advances premises only in response to authoritative character events."""

    def __init__(
        self,
        rng: random.Random,
        templates: tuple[AdventureTemplate, ...] = DEFAULT_ADVENTURES,
        *,
        max_idle_ticks: int = 120,
    ) -> None:
        if not templates:
            raise ValueError("at least one adventure template is required")
        self.rng = rng
        self.templates = templates
        self.max_idle_ticks = max_idle_ticks
        self.last_error: str | None = None
        self.last_start_event: Event | None = None
        self._world: World | None = None

    def bind(self, world: World) -> None:
        if self._world is world:
            return
        self._world = world
        world.events.subscribe(self.observe)

    @property
    def active(self) -> Adventure | None:
        if self._world is None:
            return None
        return next(
            (
                adventure
                for adventure in self._world.adventures.values()
                if adventure.status is AdventureStatus.ACTIVE
            ),
            None,
        )

    async def maybe_start(
        self,
        world: World,
        provider: AIProvider,
        world_summary: Mapping[str, object],
        timeout_seconds: float,
    ) -> Event | None:
        self.bind(world)
        if self.active is not None:
            return None
        if any(template.zones for template in self.templates):
            available = list(self.templates)
        else:
            used_templates = {
                template.id
                for template in self.templates
                if any(adventure.id.startswith(f"{template.id}_") for adventure in world.adventures.values())
            }
            available = [template for template in self.templates if template.id not in used_templates]
        if not available:
            return None
        occupied = sorted(
            {
                character.location_id
                for character in world.characters.values()
                if character.location_id != available[0].hidden_location_id
            }
        )
        preferred_index = len(world.adventures) % len(available)
        candidates = [
            {
                "template_id": template.id,
                "origin_location_id": (
                    "center_stage"
                    if template.zones and "center_stage" in world.locations
                    else self.rng.choice(occupied)
                ),
                "title": template.title,
                "premise": template.premise,
                "world_theme": template.world_theme,
                "quest_objective": template.quest_objective,
                "score": 0.98 if index == preferred_index else self._score_template(template, world) * 0.68,
            }
            for index, template in enumerate(available)
        ]
        try:
            raw = await asyncio.wait_for(
                provider.generate_structured(
                    "adventure_premise",
                    {"world_summary": dict(world_summary), "candidates": candidates},
                ),
                timeout=timeout_seconds,
            )
            template_id, origin_id = self._parse_selection(raw, candidates)
            template = next(item for item in available if item.id == template_id)
            adventure = self._instantiate(template, origin_id, world)
            event = world.start_adventure(
                adventure,
                pocket_zones=tuple(
                    {
                        "slug": zone.slug,
                        "name": zone.name,
                        "description": zone.description,
                        "danger": zone.danger,
                        "features": dict(zone.features),
                    }
                    for zone in template.zones
                ),
            )
            self.last_start_event = event
            self.last_error = None
            return event
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            return None

    def observe(self, event: Event) -> None:
        world = self._world
        adventure = self.active
        if world is None or adventure is None or not event.actor_id:
            return
        try:
            if (
                event.kind is EventKind.INSPECTED
                and event.data.get("target_id") == adventure.hook_feature_id
                and adventure.phase is AdventurePhase.HOOK
            ):
                world.advance_adventure(
                    adventure.id,
                    AdventurePhase.INVESTIGATION,
                    actor_id=event.actor_id,
                    cause_event_sequence=event.sequence,
                )
            elif (
                event.kind is EventKind.OBJECT_DISCOVERED
                and event.data.get("object_id") == adventure.clue_object_id
                and adventure.phase in {AdventurePhase.HOOK, AdventurePhase.INVESTIGATION}
            ):
                if adventure.phase is AdventurePhase.HOOK:
                    world.advance_adventure(
                        adventure.id,
                        AdventurePhase.INVESTIGATION,
                        actor_id=event.actor_id,
                        cause_event_sequence=event.sequence,
                    )
                world.advance_adventure(
                    adventure.id,
                    AdventurePhase.DISCOVERY,
                    actor_id=event.actor_id,
                    cause_event_sequence=event.sequence,
                )
            elif (
                event.kind is EventKind.MOVED
                and event.data.get("to") == adventure.hidden_location_id
                and adventure.phase is AdventurePhase.DISCOVERY
            ):
                world.advance_adventure(
                    adventure.id,
                    AdventurePhase.ESCALATION,
                    actor_id=event.actor_id,
                    cause_event_sequence=event.sequence,
                )
            elif (
                event.kind is EventKind.INSPECTED
                and event.data.get("target_id") == adventure.escalation_feature_id
                and adventure.phase is AdventurePhase.ESCALATION
            ):
                world.advance_adventure(
                    adventure.id,
                    AdventurePhase.RESOLUTION,
                    actor_id=event.actor_id,
                    cause_event_sequence=event.sequence,
                )
        except ValueError as exc:
            self.last_error = f"progression validation: {exc}"

    def maintain(self, world: World) -> Event | None:
        adventure = self.active
        if adventure and world.time.day > adventure.created_day:
            return world.expire_adventure(
                adventure.id,
                "Caine closed the pocket world at the end of its scheduled circus day.",
            )
        if adventure and world.tick - adventure.last_progress_tick >= self.max_idle_ticks:
            return world.expire_adventure(
                adventure.id,
                "The unexplained signal faded after nobody advanced the investigation.",
            )
        return None

    @staticmethod
    def _score_template(template: AdventureTemplate, world: World) -> float:
        curiosity = sum(
            character.personality.curiosity for character in world.characters.values()
        ) / max(1, len(world.characters))
        discovery_goals = max(
            (
                goal.priority
                for character in world.characters.values()
                for goal in character.goals
                if "discover" in goal.tags or "explore" in goal.tags
            ),
            default=0.0,
        )
        return min(1.0, 0.35 + curiosity * 0.3 + discovery_goals * 0.35)

    @staticmethod
    def _parse_selection(
        raw: Mapping[str, Any], candidates: list[dict[str, Any]]
    ) -> tuple[str, str]:
        if not isinstance(raw, Mapping):
            raise ValueError("adventure selection must be an object")
        template_id = raw.get("template_id")
        origin_id = raw.get("origin_location_id")
        allowed = {
            (candidate["template_id"], candidate["origin_location_id"])
            for candidate in candidates
        }
        if (template_id, origin_id) not in allowed:
            raise ValueError("adventure selection was not an offered candidate")
        return str(template_id), str(origin_id)

    @staticmethod
    def _instantiate(
        template: AdventureTemplate, origin_id: str, world: World
    ) -> Adventure:
        number = len(world.adventures) + 1
        prefix = f"{template.id}_{number}"
        return Adventure(
            id=prefix,
            title=template.title,
            premise=template.premise,
            mystery=template.mystery,
            stakes=template.stakes,
            origin_location_id=origin_id,
            hidden_location_id=template.hidden_location_id,
            hook_feature_id=f"{prefix}_hook",
            hook_description=template.hook_description,
            clue_object_id=f"{prefix}_clue",
            clue_name=template.clue_name,
            clue_description=template.clue_description,
            escalation_feature_id=f"{prefix}_core",
            escalation_description=template.escalation_description,
            world_theme=template.world_theme,
            quest_objective=template.quest_objective,
        )
