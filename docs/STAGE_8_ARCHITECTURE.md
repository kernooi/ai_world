# Stage 8 - Emergent Adventures

Stage 8 adds persistent multi-step situations to the Stage 7 simulation. It does not
add scripts that assign character behavior. The demonstration template, **The Echo
Below**, defines world conditions and transition rules; the residents decide whether,
when, and by whom those conditions are engaged.

## Lifecycle

```text
Director selects a compatible premise
        |
World validates and creates a local hook plus a hidden clue
        |
Character independently inspects hook
        |
INVESTIGATION
        |
Character independently searches and discovers clue
        |
DISCOVERY: world opens a previously inaccessible location
        |
Character independently travels there
        |
ESCALATION: world exposes the unstable source
        |
Character independently inspects the source
        |
RESOLUTION with participants, resolving character, outcome, and event history
```

The transition engine responds to ordinary `INSPECTED`, `OBJECT_DISCOVERED`, and
`MOVED` events. It never emits an `Action` and has no API for assigning one.

## Ownership and validation

- `AdventureManager` matches real world events to data-driven transition rules.
- `World.start_adventure`, `World.advance_adventure`, and
  `World.expire_adventure` validate and apply all narrative/physical state.
- Each transition requires the exact prior phase, a real character actor, and the
  sequence number of the causative event.
- Opening the hidden location, adding the escalation feature, and recording the
  outcome occur only inside the authoritative world.
- Only one prototype adventure is active at once. Completed history remains stored.

## Autonomy and knowledge

Characters receive only adventures present in their own acquired knowledge. A
resident at the hook location perceives the start; a remote resident does not.
Conversation can share awareness, but statements are recorded with their source and
confidence. Adventure-aware action scoring uses personality, bravery, curiosity,
goals, emotion, relationships, and retrieved memories. It increases opportunity
salience but does not force an action.

Consequently, the same premise can have different participants and timing under a
different random seed or character state. It can also expire unresolved after a
configurable inactivity limit.

## Director behavior

The Stage 7 Director remains the only situation-creating AI system. On a valid
intervention opportunity it first asks the mock provider whether an unused adventure
template fits the compact world summary. Once an adventure is active, normal
environmental interventions may continue, but phase progress belongs to character
events. Director summaries now include active phase, participants, and idle ticks.

## Persistence and debugging

Snapshots include every adventure field, physical changes such as opened paths,
phase/status, participants, causal event sequence history, resolver, and outcome.
Loading rebinds the event-driven manager so an in-progress adventure can continue.
The debug snapshot exposes this state alongside the Director's active-adventure
status without exposing model chain-of-thought.

## Acceptance boundary

Stage 8 includes one small reusable lifecycle and one demonstration template. It
does not include episode packaging, cinematic pacing, authored dialogue scenes,
camera AI, voice, graphics, Unreal integration, complex quest graphs, or the advanced
Director planned for later stages.
