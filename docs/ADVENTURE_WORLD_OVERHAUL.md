# Daily Adventure-World Overhaul

## Caine's role

Caine is the main orchestration AI. On the first tick of every world day, the Director asks
the provider to select a complete adventure proposal. The offline mock provider rotates
deterministically through the available concepts; a future real provider can choose or
generate richer structured proposals through the same boundary.

Caine controls premises, pocket-world creation, quest objectives, and time limits. He does
not issue character actions. All objective progress still requires a causal, validated
character event.

## Generated worlds and quests

Each selected `AdventureTemplate` contains a visual theme and at least three zone templates.
`World.start_adventure()` validates the entire plan, creates uniquely identified locations,
connects them as a pocket-world graph, and keeps the entry sealed until the portal key is
found. Four explicit objectives cover the briefing, key discovery, world entry, and finale.
Each completed objective stores its character and tick.

The initial offline catalog includes glitch-midway, moon-funfair, candy-kingdom,
clockwork-sky, storybook-sea, and neon-city concepts. Reusing a concept still creates new
location IDs and a new persistent world instance. An unfinished world expires at the next
day boundary, after which Caine immediately launches the new day's adventure.

## Character participation

Caine's announcement is a circus-wide fact, so every cast member knows the premise and
objective. Character policies receive only their own perception and knowledge. Quest-aware
navigation raises the priority of the next graph step, but the normal personality, emotion,
memory, energy, and relationship scores still compete. Resolution always identifies the
character whose causal action completed the finale. Once a quest ends, characters inside
the pocket world independently prioritize the graph route back to the circus.

Mock dialogue is assembled from the active adventure, objective, location, meaningful
recent event, target, and character-specific voice style. It is intentionally deterministic
and remains a test substitute for model-generated dialogue.

## Browser world and locomotion

The persistent circus hub now extends beyond the main tent into the Endless Circus Grounds,
Rides Promenade, Digital Lake, Adventure Portal Gallery, Grand Digital Theater, and Void
Overlook. Generated zones are placed in separate distant clusters and receive procedural
geometry and colors based on their world theme.

The old `NAV_ROUTES` waypoint table is gone. Characters use frame-by-frame steering with
acceleration, smooth turning, arrival slowdown, and separation from nearby characters.
Crossing the hub/pocket boundary uses a portal departure and arrival transition. The Python
location graph remains authoritative; the browser only interpolates its visual result.
