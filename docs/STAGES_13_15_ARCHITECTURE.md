# Stages 13–15: Expression, Camera AI, and Advanced Direction

## Stage 13 — Facial animation and expressiveness

Each procedural character rig exposes eyes, brows, a mouth, head meshes, and limb joints.
The public dominant emotion selects target eye openness, brow angle, mouth proportions,
head tilt, and resting arm posture. Rendering interpolates toward those targets so state
changes do not snap. A deterministic blink cycle and speech-driven body movement keep
characters alive between actions. Event gestures temporarily take priority, then blend
back into the emotional pose.

These expressions visualize existing public emotion values. They neither infer private
reasoning nor feed decisions back into the simulation.

## Stage 14 — Camera AI

The browser camera director scores each authoritative event using importance plus bonuses
for adventures, conversation, and environmental change. It can frame:

- one active character in a close or medium shot;
- two participants around their shared midpoint;
- a location or world event in a wide shot;
- Caine when a daily adventure begins;
- an active-adventure participant as an automatic follow shot.

Camera target and radius use eased transitions. Quiet periods produce an establishing
shot. Pointer input grants a twelve-second manual override, and the persistent Cinematic
toggle can disable automatic framing entirely. Camera choice affects presentation only.

## Stage 15 — Advanced Director

Caine now maintains a small, serializable pacing state:

```text
tension, arc stage, quiet ticks, focus character,
development opportunity, major-event count, world-expansion count
```

Tension combines current adventure phase, the strongest fear/anxiety pressure,
relationship tension, and recent activity. Adventure phases map to setup, rising action,
revelation, crisis, and recovery. During intermissions Caine identifies the character with
the strongest development pressure and offers a circumstance tailored to that person's
values—never a forced response.

The Director candidate set can include ordinary circus disruptions, discoveries, weather,
personal spotlights, high-tension RED ALERT events, and a validated path expansion into
the Infinite Mirror Maze. Three data-driven adventure arcs can reveal the Adventure Portal,
Moonlight Funfair, and Confection Kingdom over time. Mock AI selects among these scored
candidates; `World.apply_director_event` validates the result before mutation.

Caine retains the once-per-world-day limit and has no API for issuing character actions.
Character agents remain the sole source of their choices and adventure outcomes.
