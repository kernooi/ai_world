# Stage 21 - Living world and spatial agency

Stage 21 closes the gap between a semantic room graph and the browser scene.
Python now owns a persistent local `(x, z)` position, activity destination,
walking/acting phase, and multi-step routine for every circus character. The
browser consumes that state instead of inventing random idle destinations.

## Activity affordances

The hub contains named, typed spots such as rehearsal rings, bedroom doors,
banquet seats, a prop workbench, the living map, fountain promenade, ride queues,
the pixel dock, portal console, improv mark, and boundary glass. Spots publish
capacity, supported verbs, occupancy and local coordinates. Every generated
adventure zone automatically gains arrival, landmark, quest, and shelter spots.

Accepted decisions queue a physical routine. Search, exploration and inspection
can include a follow-up comparison at another spot; social behavior approaches
its target, interacts, and reacts; rest, item use, performance and travel use
appropriate places. While a routine is active the character does not request a
new decision, preventing one semantic action every tick from producing frantic
railroad-like travel.

Spatial state is part of save format 4 and the observer-safe snapshot. Restored
worlds continue from the same position and routine. Character perceptions expose
their current activity, phase, local affordances and distances to other cast
members, providing grounded context for the current mock provider and a future
real provider.

## Browser behavior

The WebGL client converts server-local positions into the appropriate hub or
pocket-world coordinates, calculates an obstacle-clearing route, and steers to
the authoritative target. Server-controlled characters no longer start random
idle walks. Occupied activity spots pulse on the floor, cards show the current
phase and active routine step, Gloinks have bodies, eyes and feet, and rides and
portals animate continuously.

## Current boundary

World consequences are still validated and committed by the existing semantic
action executor when a character makes a decision. Stage 21 paces subsequent
decisions and performs the resulting routine, but reach distance is not yet an
additional prerequisite for committing an action. Locations remain the primary
unit for item and social validation. This preserves the established simulation
contract while making spatial state persistent and model-visible.

The mock AI remains appropriate for testing this stage. A real model would add
more varied choices and dialogue, but would use the same validated actions,
activity spots and spatial context rather than controlling meshes directly.

## Verification

`tests/test_stage_21_living_world.py` covers public spatial state, movement toward
stable targets, multi-step plans, persistence, automatic generated-world spots,
and perception grounding. The browser is also exercised live to confirm that all
six cast members use server control, occupy clear navigation space, and expose
their activity in the observer cards.
