from __future__ import annotations

from autonomous_ai_world.models import Action, ActionKind, Character, EventKind, Location
from autonomous_ai_world.world import World


def make_world() -> World:
    return World(
        locations=[
            Location(
                "square",
                "Square",
                "An open square.",
                exits={"garden"},
                features={"clock": "The clock is five minutes slow."},
            ),
            Location(
                "garden",
                "Garden",
                "A quiet garden.",
                exits={"square"},
                features={"pond": "A frog watches from a lily pad."},
            ),
            Location("tower", "Tower", "A remote tower."),
        ],
        characters=[
            Character("ada", "Ada", "square"),
            Character("ben", "Ben", "square"),
            Character("cy", "Cy", "tower"),
        ],
    )


def test_move_is_validated_and_executed_by_world() -> None:
    world = make_world()

    result = world.execute(Action("ada", ActionKind.MOVE, target_id="garden"))

    assert result.accepted
    assert result.event.kind is EventKind.MOVED
    assert world.characters["ada"].location_id == "garden"
    assert world.characters["ada"].energy == 6


def test_non_adjacent_move_is_rejected_without_mutating_state() -> None:
    world = make_world()

    result = world.execute(Action("ada", ActionKind.MOVE, target_id="tower"))

    assert not result.accepted
    assert result.event.kind is EventKind.ACTION_REJECTED
    assert world.characters["ada"].location_id == "square"
    assert world.characters["ada"].energy == 8


def test_unknown_action_kind_is_rejected_instead_of_reaching_execution() -> None:
    world = make_world()
    malformed = Action("ada", "teleport", target_id="tower")  # type: ignore[arg-type]

    result = world.execute(malformed)

    assert not result.accepted
    assert result.event.kind is EventKind.ACTION_REJECTED
    assert result.event.data["reason"] == "unsupported action kind 'teleport'"
    assert world.characters["ada"].location_id == "square"


def test_character_cannot_talk_to_someone_outside_local_perception() -> None:
    world = make_world()

    result = world.execute(
        Action("ada", ActionKind.TALK, target_id="cy", message="Can you hear me?")
    )

    assert not result.accepted
    assert result.event.data["reason"] == "Cy is not here"


def test_perception_contains_only_local_state_and_relevant_events() -> None:
    world = make_world()
    world.create_situation(
        location_id="garden",
        feature_id="seed",
        description="A golden seed hums softly.",
        title="a golden seed appears",
    )

    perception = world.perceive("ada")

    assert perception.location_id == "square"
    assert perception.nearby_characters == ("ben",)
    assert set(perception.features) == {"clock"}
    assert all(event.location_id == "square" for event in perception.recent_events)


def test_inspection_requires_a_locally_perceivable_target() -> None:
    world = make_world()

    rejected = world.execute(Action("ada", ActionKind.INSPECT, target_id="pond"))
    accepted = world.execute(Action("ada", ActionKind.INSPECT, target_id="clock"))

    assert not rejected.accepted
    assert accepted.accepted
    assert accepted.event.data["detail"] == "The clock is five minutes slow."


def test_rest_recovers_energy_without_exceeding_maximum() -> None:
    world = make_world()
    world.characters["ada"].energy = 9

    result = world.execute(Action("ada", ActionKind.REST))

    assert result.accepted
    assert world.characters["ada"].energy == 10
    assert result.event.data["energy_after"] == 10
