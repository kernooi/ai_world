from __future__ import annotations

from autonomous_ai_world.models import Action, ActionKind
from autonomous_ai_world.simulation import create_default_simulation


def test_help_increases_targets_trust_and_friendship() -> None:
    simulation = create_default_simulation(seed=1)
    before = simulation.relationships.get("bob", "alice")
    trust_before = before.trust
    friendship_before = before.friendship

    result = simulation.world.execute(Action("alice", ActionKind.HELP, target_id="bob"))

    after = simulation.relationships.get("bob", "alice")
    assert result.accepted
    assert after.trust > trust_before
    assert after.friendship > friendship_before
    assert simulation.memory.store_for("bob").long_term


def test_lie_reduces_targets_trust_and_increases_suspicion() -> None:
    simulation = create_default_simulation(seed=1)
    relation = simulation.relationships.get("alice", "bob")
    trust_before = relation.trust
    suspicion_before = relation.suspicion

    result = simulation.world.execute(
        Action("bob", ActionKind.LIE, target_id="alice", message="There is no compass.")
    )

    assert result.accepted
    assert relation.trust < trust_before
    assert relation.suspicion > suspicion_before
    assert simulation.world.characters["alice"].emotions.anger > 0


def test_relationships_are_directional() -> None:
    simulation = create_default_simulation(seed=1)
    alice_view_before = simulation.relationships.get("alice", "bob").trust
    bob_view_before = simulation.relationships.get("bob", "alice").trust

    simulation.world.execute(Action("alice", ActionKind.HELP, target_id="bob"))

    assert simulation.relationships.get("alice", "bob").trust == alice_view_before
    assert simulation.relationships.get("bob", "alice").trust > bob_view_before

