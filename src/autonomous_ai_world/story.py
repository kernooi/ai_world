"""Action-driven candy rescue: persisted scenes, physical work and consequences.

Inspect chooses an interaction; only arriving and performing its spatial routine
counts as work. A timer can fail a scene, but never completes one for the cast.
"""
from autonomous_ai_world.models import AdventurePhase, AdventureStatus, EventKind, KnowledgeFact


SCENES = (
    ("A sweet welcome", 0, "Free the sugar workers", 2,
     "Pip", "You came for a royal banquet? The factory locked my friends inside its delivery cages!", "cages"),
    ("The delivery line", 1, "Repair the conveyor together", 3,
     "Pip", "Keep that belt running! The workers cannot cross the boiling caramel on foot.", "conveyor"),
    ("The foreman's offer", 1, "Choose: rescue the last worker or take the shortcut", 1,
     "Foreman Fudge", "Leave that last cage. My express lift will get you out before anyone notices.", "choice"),
    ("The banquet was a trap", 2, "Vent the runaway sugar furnace", 3,
     "Foreman Fudge", "You were never guests. The crown ordered six new ingredients. Seal the doors!", "furnace"),
    ("Run for the delivery dock", 0, "Hold the escape gate for the group", 3,
     "Pip", "The furnace is cracking! Get back to my truck. Hold the gate while we load everyone!", "escape"),
)

REACTIONS = {
    'pomni': ('They put locks on the outside. This is not a tour.', 'Please tell me this belt leads away from the boiling stuff.', 'We cannot just leave someone here.', 'Of course the banquet needs ingredients. Of course it does.', 'Keep moving! I have the gate!'),
    'ragatha': ('Stay back from the bars. We are getting you out.', 'One at a time. I will help you across.', 'Nobody gets left in a cage.', 'Pip, stay behind me. We can still fix this.', 'Count everyone before we close it!'),
    'jax': ('A rescue mission? Fine. Breaking locks is the fun part.', 'Try not to become caramel filling.', 'The express exit sounds better than more unpaid heroics.', 'So the creepy foreman lied. Shocking.', 'Truck leaves now. Last one in gets the sticky seat.'),
    'gangle': ('They look scared. I know that feeling.', 'I can hold this cable. Just do not pull too hard.', 'What if that last worker were one of us?', 'I am scared, but I am not letting go of this valve.', 'Here! Follow my ribbon to the truck!'),
    'kinger': ('A cage! No, wait. A cage with someone in it. We should help.', 'Conveyors. Like ants, but with worse working conditions.', 'A shortcut is only short if you come out the other side.', 'Pressure valves! I remember how these work. I think.', 'I counted the workers twice. Same number both times!'),
    'zooble': ('Caine, your vacation package needs work.', 'Stop yanking it. The drive roller is jammed.', 'I do not trust that foreman. Check the other door.', 'Give me room. This vent is coming off.', 'Door held. Get in the truck already.'),
}


def current_scene(adventure):
    state = adventure.story
    return SCENES[min(state.get('scene', 0), len(SCENES)-1)]


def scene_location(adventure):
    return adventure.generated_location_ids[current_scene(adventure)[1]]


def target_id(adventure, choice='work'):
    return f'{adventure.id}:story:{adventure.story.get("scene", 0)}:{choice}'


def emit(world, adventure, text, speaker='Pip', actor_id=None):
    event = world._event(EventKind.ADVENTURE_PROGRESSED,
        world.characters.get(actor_id), text,
        {'adventure_id': adventure.id, 'story_scene': adventure.story['scene'],
         'speaker': speaker, 'story_dialogue': True,
         'story_location_id': scene_location(adventure)}, importance=.95)
    adventure.event_sequences.append(event.sequence)
    world.events.publish(event)


def enter_scene(world, adventure):
    state = adventure.story
    title, _, objective, required, speaker, line, mechanism = current_scene(adventure)
    state.update(title=title, objective=objective, required=required, mechanism=mechanism,
                 contributors=[], pending={}, started_tick=world.tick, progress=0,
                 location_id=scene_location(adventure), speaker=speaker, dialogue=line,
                 deadline_tick=world.tick + (48 if mechanism in {'furnace','escape'} else 100))
    location = world.locations[state['location_id']]
    choices = ['rescue','shortcut'] if mechanism == 'choice' else ['work']
    state['targets'] = [{'id': target_id(adventure, choice), 'choice': choice,
                         'x': -5 if choice != 'shortcut' else 5, 'z': -4,
                         'label': 'Release the last worker' if choice == 'rescue' else
                                  'Take the foreman’s shortcut' if choice == 'shortcut' else objective}
                        for choice in choices]
    for target in state['targets']:
        location.features[target['id']] = target['label']
    emit(world, adventure, line, speaker)


def begin_story(world, adventure):
    adventure.story = {'scene': 0, 'branch': None, 'rescued': 0, 'history': [], 'done': False}
    enter_scene(world, adventure)


def offer(world, adventure, character_id):
    if not adventure.story or adventure.story.get('done') or adventure.phase != AdventurePhase.ESCALATION:
        return {}
    state = adventure.story
    character = world.characters[character_id]
    choices = state['targets']
    preferred = 'shortcut' if character.personality.risk_tolerance > .65 and character.personality.empathy < .5 else 'rescue'
    target = next((t for t in choices if t['choice'] == preferred), choices[0])
    return {'story_target_id': target['id'] if character_id not in state['contributors'] else '',
            'story_location_id': state['location_id'], 'story_objective': state['objective']}


def record_interaction(world, adventure, event):
    state = adventure.story
    if not state or state.get('done') or adventure.phase != AdventurePhase.ESCALATION:
        return
    target = next((t for t in state['targets'] if t['id'] == event.data.get('target_id')), None)
    if target and event.location_id == state['location_id']:
        state['pending'][event.actor_id] = {'target': target['id'], 'cause': event.sequence}


def advance_story(world):
    for adventure in list(world.adventures.values()):
        state = adventure.story
        if not state or state.get('done') or adventure.status != AdventureStatus.ACTIVE or adventure.phase != AdventurePhase.ESCALATION:
            continue
        if world.tick >= state['deadline_tick']:
            state['done'] = True
            state['failed'] = True
            state['dialogue'] = 'Caine opens an emergency exit. The factory is lost; the unfinished rescue stays with the cast.'
            world.expire_adventure(adventure.id, state['dialogue'])
            remember(world, adventure, state['dialogue'])
            continue
        state['remaining_ticks'] = state['deadline_tick'] - world.tick
        for actor_id, pending in list(state['pending'].items()):
            spatial = world.living_world.characters.get(actor_id)
            target = next((t for t in state['targets'] if t['id'] == pending['target']), None)
            if not spatial or not target or actor_id in state['contributors']:
                continue
            if spatial.location_id != state['location_id'] or spatial.phase != 'acting' or spatial.dwell > 0:
                continue
            if not spatial.plan or spatial.plan_index >= len(spatial.plan) or spatial.plan[spatial.plan_index].target_id != target['id']:
                continue
            state['contributors'].append(actor_id)
            state['progress'] = len(state['contributors'])
            adventure.participants.add(actor_id)
            adventure.last_progress_tick = world.tick
            name = world.characters[actor_id].name
            words = REACTIONS.get(actor_id, ('Working on it.',)*5)[state['scene']]
            emit(world, adventure, words, name, actor_id)
            if state['mechanism'] == 'choice':
                state['branch'] = target['choice']
                if target['choice'] == 'rescue':
                    state['rescued'] += 1
                emit(world, adventure, 'You came back for me. I know the furnace’s emergency vent!' if target['choice']=='rescue'
                     else 'Express lift? That door just locked behind us!', 'Pip')
            if state['progress'] < state['required']:
                continue
            if state['mechanism'] == 'cages':
                state['rescued'] = 2
            state['history'].append({'title': state['title'], 'tick': world.tick,
                                     'contributors': list(state['contributors']), 'branch': state['branch']})
            for item in state['targets']:
                world.locations[state['location_id']].features.pop(item['id'], None)
            state['scene'] += 1
            if state['scene'] == len(SCENES):
                state['done'] = True
                outcome = f'The delivery truck escapes with {state["rescued"]} sugar workers. ' + (
                    'Pip returns as a friend; the cast saved the last worker.' if state['branch']=='rescue' else
                    'The shortcut saved time, but a worker was left behind. The cast must live with that choice.')
                # Resolve only after all physical scene work, with a real final
                # interaction as the causal event (validated in World).
                state['outcome'] = outcome
                world.advance_adventure(adventure.id, AdventurePhase.RESOLUTION,
                    actor_id=actor_id, cause_event_sequence=pending['cause'])
                adventure.outcome = outcome
                state['dialogue'] = outcome
                emit(world, adventure, outcome, 'Caine')
                remember(world, adventure, outcome)
            else:
                enter_scene(world, adventure)
                if state['mechanism'] == 'furnace' and state['branch'] == 'rescue':
                    state['required'] = 2
                    state['dialogue'] = 'Pip opens a service vent: saving the worker makes the furnace easier to stop.'
            break


def remember(world, adventure, outcome):
    for character in world.characters.values():
        character.knowledge[f'factory:{adventure.id}'] = KnowledgeFact(
            f'factory:{adventure.id}', outcome, world.tick, 'experienced adventure')
