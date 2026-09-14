from autonomous_ai_world.simulation import create_circus_simulation, Simulation
from autonomous_ai_world.models import Action, ActionKind, AdventurePhase, AdventureStatus
from autonomous_ai_world.story import enter_scene, advance_story


def started():
    sim = create_circus_simulation(seed=7)
    for _ in range(30):
        sim.step()
        adventure = next(iter(sim.world.adventures.values()))
        if adventure.story:
            return sim, adventure
    raise AssertionError('story never opened')


def test_inspection_and_time_alone_cannot_complete_a_rescue():
    sim, adventure = started()
    actor = 'pomni'
    sim.world.characters[actor].location_id = adventure.story['location_id']
    target = adventure.story['targets'][0]['id']
    result = sim.world.execute(Action(actor, ActionKind.INSPECT, target))
    assert result.accepted
    # No corresponding spatial work was queued/performed.
    for _ in range(4):
        sim.world.tick += 1
        advance_story(sim.world)
    assert adventure.story['progress'] == 0
    assert adventure.status is AdventureStatus.ACTIVE


def test_story_requires_multiple_contributors_and_remembers_the_ending():
    sim = create_circus_simulation(seed=7)
    sim.run(90)
    adventure = next(iter(sim.world.adventures.values()))
    assert adventure.status is AdventureStatus.RESOLVED
    assert len(adventure.story['history']) == 5
    assert all(len(s['contributors']) >= 2 for s in adventure.story['history'] if s['title'] != "The foreman's offer")
    assert all(f'factory:{adventure.id}' in c.knowledge for c in sim.world.characters.values())
    assert '3 sugar workers' in adventure.outcome
    assert any('3 sugar workers' in outcome for outcome in sim.episodes.episodes[0].key_outcomes)


def test_scene_timeout_evacuates_without_faking_success():
    sim, adventure = started()
    sim.world.tick = adventure.story['deadline_tick']
    advance_story(sim.world)
    assert adventure.status is AdventureStatus.EXPIRED
    assert adventure.story['failed']
    assert adventure.objectives[-1].status == 'pending'


def test_both_choices_change_the_furnace_work_required():
    for choice, required, rescued in [('rescue',2,3),('shortcut',3,2)]:
        sim, adventure = started()
        adventure.story.update(scene=2, rescued=2)
        enter_scene(sim.world, adventure)
        target = next(t for t in adventure.story['targets'] if t['choice'] == choice)
        actor = sim.world.characters['jax']
        actor.location_id = adventure.story['location_id']
        action = Action('jax', ActionKind.INSPECT, target['id'])
        assert sim.world.execute(action).accepted
        sim.living_world.queue_actions([action], sim.world)
        for _ in range(12):
            sim.world.tick += 1
            sim.living_world.advance(sim.world)
            advance_story(sim.world)
            if adventure.story['scene'] == 3:
                break
        assert adventure.story['scene'] == 3
        assert adventure.story['branch'] == choice
        assert adventure.story['required'] == required
        assert adventure.story['rescued'] == rescued


def test_active_story_and_pending_work_survive_reload():
    sim, adventure = started()
    sim.run(5)
    restored = Simulation.from_dict(sim.to_dict(), seed=7)
    assert restored.world.adventures[adventure.id].story == adventure.story
    restored.run(100)
    assert restored.world.adventures[adventure.id].status in {AdventureStatus.RESOLVED, AdventureStatus.EXPIRED}
