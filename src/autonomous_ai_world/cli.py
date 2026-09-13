"""Observer-only text presentation for the complete autonomous circus backend."""

from __future__ import annotations

import argparse
import json
import time

from autonomous_ai_world.ai import AIProviderError
from autonomous_ai_world.config import Settings
from autonomous_ai_world.debug import debug_snapshot
from autonomous_ai_world.models import EventKind
from autonomous_ai_world.persistence import JsonStateRepository, PersistenceError
from autonomous_ai_world.simulation import Simulation, create_circus_simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-world", description="Observe Caine's autonomous daily adventure worlds."
    )
    parser.add_argument("--steps", type=int, default=10, help="simulation cycles (default: 10)")
    parser.add_argument("--seed", type=int, default=None, help="seed for a repeatable run")
    parser.add_argument("--delay", type=float, default=0.0, help="seconds between cycles")
    parser.add_argument("--debug", action="store_true", help="print a final state inspector")
    parser.add_argument("--save-state", metavar="PATH", help="atomically save state after the run")
    parser.add_argument("--load-state", metavar="PATH", help="continue a saved world")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.steps < 0:
        raise SystemExit("--steps must be zero or greater")
    if args.delay < 0:
        raise SystemExit("--delay must be zero or greater")
    settings = Settings.from_env()
    try:
        settings.validate_runtime()
        if args.load_state:
            simulation = Simulation.load(
                JsonStateRepository(args.load_state), seed=args.seed or 0, settings=settings
            )
        else:
            simulation = create_circus_simulation(seed=args.seed, settings=settings)
    except (AIProviderError, PersistenceError) as exc:
        raise SystemExit(str(exc)) from exc

    print("=" * 58)
    print("THE AUTONOMOUS DIGITAL CIRCUS - DAILY QUEST WORLDS (MOCK AI)")
    print("Observer mode: characters choose their own actions.")
    print("=" * 58)
    for _ in range(args.steps):
        events = simulation.step()
        print(f"\n{simulation.world.time.label} | Weather: {simulation.world.weather.value}")
        for event in events:
            marker = simulation.director.name.upper() if event.actor_id is None else event.actor_id.upper()
            rejected = " [REJECTED]" if event.kind is EventKind.ACTION_REJECTED else ""
            print(f"[{event.sequence:04d}] {marker}{rejected}: {event.summary}")
        if args.delay:
            time.sleep(args.delay)

    print("\nCHARACTER STATE")
    for character in simulation.world.characters.values():
        location = simulation.world.locations[character.location_id]
        goal = max(character.goals, key=lambda item: item.priority).description
        intention = character.current_intention.description if character.current_intention else "none"
        print(
            f"- {character.name}: {location.name}; goal={goal}; "
            f"intention={intention}; energy={character.energy}"
        )
    print(
        f"{simulation.director.name}: {simulation.director.status}; "
        f"cooldown={simulation.director.cooldown_remaining}"
    )
    for adventure in simulation.world.adventures.values():
        print(
            f"Adventure: {adventure.title}; phase={adventure.phase.value}; "
            f"status={adventure.status.value}; quest={adventure.quest_objective}; "
            f"participants={','.join(sorted(adventure.participants)) or 'none'}"
        )

    if args.save_state:
        try:
            simulation.save(JsonStateRepository(args.save_state))
            print(f"State saved to {args.save_state}")
        except PersistenceError as exc:
            raise SystemExit(str(exc)) from exc
    if args.debug:
        print("\nDEBUG SNAPSHOT")
        print(json.dumps(debug_snapshot(simulation), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
