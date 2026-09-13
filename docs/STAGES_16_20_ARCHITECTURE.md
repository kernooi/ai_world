# Stages 16–20 Architecture

## Stage 16 — Persistent world

`Simulation.to_dict()` is the complete cross-session boundary (schema version 3). It
contains authoritative world state and history, private memory, relationships and
discoveries, Director pacing, psychology, circus systems, episodes, and consequences.
`JsonStateRepository` writes atomically and preserves a `.backup` generation. Loading
falls back to that generation if the primary file is missing or malformed. Existing
circus saves load with defaults and the web host fills new character profiles safely.

## Stage 17 — Advanced world simulation

`CircusSystems` is an event projection, not a second authority. It observes accepted
world events and maintains digital stability, audience excitement, cast cohesion, prop
condition, supplies, show phases, Gloink population, faction influence, and set history.
Its deterministic `advance()` makes simulation runs reproducible. Shared pressure feeds
back into character anxiety, fear, excitement, and loneliness, affecting later decisions.
The browser treats the
projection as presentation data and materializes up to twelve procedural Gloink NPCs.

## Stage 18 — Advanced character psychology

Every `Character` owns persistent `CharacterPsychology` with identity, history, ambition,
beliefs, conflicts, standing, reputation, habits, and secrets. The simulation derives
changes from events. The candidate policy uses habits and public standing as bounded
score modifiers; all resulting actions still pass normal world validation. A character's
private provider context includes its own secrets, but `world_snapshot()` intentionally
publishes only identity, ambition, standing, reputation, and strongest habit.

## Stage 19 — Production presentation

The asset-free Babylon.js client adds dynamic show lights, rotating portal layers,
population animation, event confetti, glitch transitions, procedural ambient audio,
event cues, and system/episode UI. Speech and audio require the browser's first user
gesture. Rendering adapts its hardware scaling from measured frame rate and pauses when
the tab is hidden. These features do not feed commands back into character behavior.

## Stage 20 — Episode system

`EpisodeManager` subscribes to the same immutable event stream. A Director incident opens
an episode; relevant actors, major sequences, memorable events, and consequences accrue
as facts arrive. Resolution/expiry closes adventure episodes, while the next day closes
an unfinished situation episode. The chronicle is dynamic, persisted, and included in
observer-safe snapshots, so it survives long after the bounded live event panel scrolls.

The dependency direction remains:

```text
validated actions -> authoritative World -> immutable events
                                           |-> memory / relationships / psychology
                                           |-> circus systems
                                           |-> episode chronicle
                                           `-> observer-safe browser presentation
```
