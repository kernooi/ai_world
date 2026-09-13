from __future__ import annotations

from autonomous_ai_world.models import (
    Action,
    ActionKind,
    DirectorEventKind,
    DirectorEventRequest,
    EventKind,
    Weather,
)
from autonomous_ai_world.simulation import create_default_simulation


def test_world_time_and_needs_advance_deterministically() -> None:
    simulation = create_default_simulation(seed=1)

    simulation.world.advance_tick(minutes=30)

    assert simulation.world.time.label == "Day 1 - 08:30"
    assert all(character.physical_state.hunger == 1 for character in simulation.world.characters.values())


def test_hidden_object_is_known_only_to_character_who_searches() -> None:
    simulation = create_default_simulation(seed=1)
    world = simulation.world

    assert "old_compass" not in world.perceive("charlie").visible_objects
    result = world.execute(Action("charlie", ActionKind.SEARCH))

    assert result.event.kind is EventKind.OBJECT_DISCOVERED
    assert "old_compass" in world.perceive("charlie").visible_objects
    assert "object:old_compass" in world.characters["charlie"].knowledge
    assert "object:old_compass" not in world.characters["alice"].knowledge


def test_item_lifecycle_is_validated_and_authoritative() -> None:
    simulation = create_default_simulation(seed=1)
    world = simulation.world
    world.characters["alice"].location_id = "river"

    picked_up = world.execute(Action("alice", ActionKind.PICK_UP, target_id="river_berries"))
    used = world.execute(Action("alice", ActionKind.USE_ITEM, target_id="river_berries"))
    dropped = world.execute(Action("alice", ActionKind.DROP, target_id="river_berries"))

    assert picked_up.accepted and used.accepted and dropped.accepted
    assert "river_berries" not in world.characters["alice"].inventory
    assert world.objects["river_berries"].location_id == "river"
    assert world.objects["river_berries"].uses_remaining == 1


def test_invalid_pickup_does_not_mutate_object_or_inventory() -> None:
    simulation = create_default_simulation(seed=1)
    world = simulation.world

    result = world.execute(Action("alice", ActionKind.PICK_UP, target_id="old_compass"))

    assert not result.accepted
    assert world.objects["old_compass"].location_id == "forest"
    assert not world.characters["alice"].inventory


def test_director_weather_request_must_change_weather() -> None:
    simulation = create_default_simulation(seed=1)
    world = simulation.world

    request = DirectorEventRequest(
        DirectorEventKind.WEATHER, "clear skies continue", weather=Weather.CLEAR
    )

    try:
        world.apply_director_event(request)
    except ValueError as exc:
        assert "must change" in str(exc)
    else:
        raise AssertionError("unchanged weather should be rejected")
    assert world.weather is Weather.CLEAR

