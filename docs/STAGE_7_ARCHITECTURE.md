# Stage 7 Architecture

> Historical milestone: the repository now implements Stage 8. This document records
> the Stage 7 boundary that the newer adventure subsystem builds upon.

## Acceptance status

The backend implements Stages 1 through 7. It remains a small text simulation and
uses `MockAIProvider` for every character and Director decision.

| Stage | Acceptance evidence |
| --- | --- |
| 2 Character brains | Personality, goals, emotion, relationship, memory, and knowledge contribute to candidate scores; tests demonstrate different choices from the same perception. |
| 3 Tool agents | Provider decisions parse into typed actions; the world performs semantic validation and is the only executor. |
| 4 Memory | Salience determines memory tier; bounded recent memory and relevance retrieval survive a save/load boundary. |
| 5 Relationships | Help, lies, and conversation update directional state, which changes later choices. |
| 6 World | Time, weather, locations, objects, inventory, needs, events, perception, and JSON persistence are authoritative. |
| 7 Director | The Director sees a compact summary, observes a cooldown, proposes only allowed circumstances, and passes proposals through world validation. |

## Invariants

1. Character agents receive `Perception`, not `World`.
2. Provider output cannot mutate state; it is parsed and checked against available
   candidates before becoming an `Action`.
3. Every action is validated again against current authoritative state at execution
   time. This handles state changes between concurrent decisions.
4. Hidden objects and remote events do not enter a character's perception or private
   knowledge unless that character legitimately observes, discovers, or is told
   about them.
5. Memory, relationships, emotion, and knowledge are deterministic projections of
   published world events.
6. The Director can call only `World.apply_director_event`; it cannot access the
   character decision channel.
7. State files are written atomically. A provider, parsing, or persistence failure
   does not partially apply a requested action.

## Decision cycle

```text
advance time and needs
        |
Director summarizes prior state
        |
optional validated intervention (cooldown controlled)
        |
capture one local perception per character
        |
retrieve relevant private memories
        |
score goal/personality/emotion/relationship-aware candidates
        |
concurrent MockAIProvider selection with timeout
        |
parse structured output or use deterministic fallback
        |
world validates and executes each action
        |
events update private memory, knowledge, emotion, and relationships
```

The mock AI is deterministic for a seed. Candidate scores include controlled random
jitter, so different seeds can yield variation without bypassing character motives
or world rules.

## Persistence scope

Saved state includes:

- world time, weather, tick, locations, exits, features, danger, and objects;
- character profiles, goals, emotions, physical state, knowledge, relationships,
  intentions, location, and inventory;
- all structured events and all memory tiers;
- Director intervention count and cooldown position.

The storage interface is intentionally small. `JsonStateRepository` is the prototype
implementation; a future PostgreSQL repository can implement the same `save/load`
contract.

## Failure behavior

- Invalid structured AI output: logged on the agent inspector; deterministic fallback
  action is used.
- AI exception or timeout: isolated per concurrent agent; fallback is used.
- Invalid action or stale target: rejected event; no requested physical mutation.
- Invalid Director event: no intervention and cooldown is not consumed.
- Save/load error: raised as `PersistenceError`; atomic replacement avoids partial
  state files.

## Stage 8 boundary

This implementation deliberately does not generate multi-step adventures, story
arcs, episodes, scripted betrayals, cinematic pacing, cameras, voice, 3D state, or
Unreal integration. Stage 8 can build adventure premises and unresolved-situation
tracking on top of the current event, memory, relationship, and Director contracts.
