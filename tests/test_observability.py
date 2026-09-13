from __future__ import annotations

from autonomous_ai_world.debug import debug_snapshot
from autonomous_ai_world.simulation import create_default_simulation


def test_debug_snapshot_exposes_required_state_without_reasoning_trace() -> None:
    simulation = create_default_simulation(seed=4)
    simulation.run(3)

    snapshot = debug_snapshot(simulation)
    alice = snapshot["characters"]["alice"]

    assert snapshot["world"]["time"] == "Day 1 - 08:30"
    assert "primary_goal" in alice
    assert "emotions" in alice
    assert "known_information" in alice
    assert "recent_memories" in alice
    assert "relationships" in alice
    assert "last_action_result" in alice
    assert "world_summary" in snapshot["director"]
    assert "chain_of_thought" not in str(snapshot).lower()
