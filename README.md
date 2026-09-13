# Autonomous AI World

A runnable, observer-only simulation implementing the project through
**Stage 20 - Episode System**. Pomni, Ragatha, Jax, Gangle, Kinger, and Zooble
independently perceive a detailed digital circus,
reason from private state through a deterministic mock AI provider, submit
structured tool actions, experience authoritative consequences, remember events,
and develop directional relationships. Caine acts as the Director and introduces
one validated challenge per world day without choosing character behavior. The live
state is presented as a procedural 3D world in a normal web browser.

No API key, database server, Unreal Engine, 3D models, or manual scene setup is required.

## Run

Python 3.11 or newer is required.

On Windows, double-click **`start_world.bat`**. The first launch creates an isolated
environment and installs the web dependencies; after that it starts the simulation
and opens `http://127.0.0.1:8765` automatically. Keep the small launcher window open
while watching the world.

Command-line equivalent:

```powershell
python -m pip install -e ".[dev]"
ai-world-web
```

Useful observer/developer options:

```powershell
ai-world --steps 6 --seed 7 --debug
ai-world --steps 10 --save-state world.json
ai-world --steps 10 --load-state world.json
```

The CLI offers observation, reproducibility, diagnostics, and session selection.
It offers no command for forcing character actions or outcomes.

## Test

```powershell
python -m pytest
```

## Implemented stages

### Stage 1 - Pure text world

- Village, Forest, Cave, and River
- Alice, Bob, and Charlie
- Observer-only chronological text output
- Central immutable event history

### Stage 2 - Character brains

- Structured personality dimensions that affect action scores
- Prioritized, potentially conflicting personal goals
- Values, fears, preferences, emotions, physical state, private knowledge, current
  intention, and independent relationships
- Decisions built only from local perception and legitimately acquired knowledge
- Explainable decision summaries without storing hidden chain-of-thought

### Stage 3 - Tool-based agents

- Structured `move`, `talk`, `inspect`, `rest`, `explore`, `search`, `pick_up`,
  `drop`, `use_item`, `sleep`, `help`, and `lie` tools
- Explicit action schemas and strict parsing of untrusted provider output
- Semantic validation and execution exclusively inside the authoritative world
- Structured accepted/rejected results with no mutation on invalid actions
- Concurrent asynchronous provider calls with timeouts and deterministic fallback

### Stage 4 - Persistent memory

- Bounded short-term, long-term, and episodic memories
- Importance-based promotion and retention
- Relevance, recency, and participant-aware retrieval
- Only a small relevant set is provided during each decision
- JSON-serializable cross-session memory

### Stage 5 - Relationships

- Directional trust, friendship, respect, suspicion, fear, anger, affection, and
  loyalty
- Deterministic changes caused by helpful, harmful, and social events
- Relationship state and relevant social memories influence later choices

### Stage 6 - World simulation

- Authoritative time, day/night, weather, location graph, danger, features, objects,
  inventories, health, energy, and hunger
- Hidden objects and character-specific discovery knowledge
- Event-driven deterministic updates to knowledge, emotion, memory, and relationships
- Atomic JSON persistence behind a replaceable repository interface

### Stage 7 - Director AI

- Separate mock-AI-backed Director agent
- Compact world summaries containing activity, character goals/intentions, recent
  events, weather, and relationship tension
- Cooldown-based interventions
- Validated situations, objects, weather changes, and world support for opening paths
- Director debug status, last summary, last event, cooldown, and error reporting
- No ability for the Director to issue or overwrite a character action

### Stage 8 - Emergent adventures

- Data-driven adventure templates with a premise, mystery, stakes, hook, clue,
  hidden location, escalation, and resolution condition
- Persistent `hook -> investigation -> discovery -> escalation -> resolution`
  lifecycle
- Adventure progress triggered exclusively by validated character actions and
  their resulting world events
- Discovery can authoritatively reveal a previously inaccessible location
- Independent characters become participants through their own actions
- Adventure knowledge remains private until perceived, experienced, or communicated
- Resolved and expired premises retain participants, event history, outcome, and
  resolving character
- The Director sees active phase, participants, and inactivity in its compact summary

### Stage 9 - Browser 3D world

- Detailed procedural circus interior with a striped tent shell, checkerboard floor,
  three rings, bleachers, trapeze, lights, curtains, bedroom doors, dining furniture,
  backstage props, and a rainbow adventure portal
- Bespoke procedural bodies for Pomni, Ragatha, Jax, Gangle, Kinger, and Zooble
- A floating procedural Caine presentation above the stage
- Caine creates at most one validated Director event per in-world calendar day
- Animated travel, activity pulses, dialogue bubbles, weather, lighting, and rain
- FastAPI snapshot endpoint and real-time WebSocket event stream
- Observer dashboard for character intentions, emotion, energy, adventures, and events
- Observer-only pause and playback-speed controls; no character-control endpoint
- Automatic reconnect, full-state resynchronization, and atomic autosave to `.runtime/`
- One-click Windows setup, launch, and browser opening

This is a fan-built procedural interpretation. The repository includes no extracted
models, textures, audio, scripts, or other production assets from the show.

### Stage 10 - Navigation and character bodies

- Multi-waypoint routes keep travel on clear lanes through the furnished circus
- Reverse-route planning and per-character lane offsets avoid visual overlap
- Scene collision metadata protects the boundary between characters and solid props
- Separate walking, talking, helping, searching, inspecting, collecting, resting,
  and sleeping body animations
- Six bespoke procedural body rigs with independently animated limbs

### Stage 11 - Real-time synchronization

- Versioned envelopes with session IDs, monotonic message IDs, and UTC server times
- Client acknowledgements, duplicate suppression, and ordered event application
- A 256-message replay buffer for short disconnects
- Full observer-safe snapshot fallback when replay history is unavailable
- Five-second heartbeat and automatic stale-connection recovery
- `GET /api/protocol` exposes the supported observer-only protocol contract

### Stage 12 - Voice

- Browser-native speech synthesis with no API key or cloud TTS account
- Distinct pitch, rate, and installed-voice preferences for all six characters and Caine
- Emotion-sensitive pitch and timing adjustments
- Ordered dialogue playback synchronized with speech bubbles and body movement
- Persistent voice on/off and volume controls
- Caine voices daily adventures and circus-wide announcements

### Stage 13 - Facial animation and expressiveness

- Emotion-driven eye size, blinking, eyebrow angle, mouth shape, and head tilt
- Fear, anxiety, anger, happiness, curiosity, and loneliness produce different poses
- Emotion-aware resting arm posture blends with event-selected gestures
- Speech timing animates the active speaker without changing simulation state

### Stage 14 - Camera AI

- Event-interest scoring selects the most important live action
- Close, medium, wide, conversation, character-follow, location, and Caine shots
- Smooth target/radius transitions and moving-character tracking
- Automatic establishing shots when the world becomes visually quiet
- Manual orbit temporarily overrides the camera AI; cinematic mode can be disabled

### Stage 15 - Advanced Director

- Persisted tension, arc stage, quiet-time, character focus, major-event, and expansion state
- Adventure phase, emotion, activity, and relationship tension drive story pacing
- Character-development opportunities tailored to each cast member
- Three multi-stage circus adventure arcs with separate pocket worlds
- Escalating major-event candidates and controlled expansion into the Infinite Mirror Maze
- Every proposal still passes world validation, and Caine still cannot select character actions

### Stage 16 - Persistent world

- Versioned full-world saves retain history, memory, discoveries, relationships, locations,
  objects, psychology, world systems, episodes, and major consequences
- Atomic autosaves keep a last-known-good backup and recover from a damaged primary save
- Older circus saves migrate forward and receive the expanded psychology profiles

### Stage 17 - Advanced world simulation

- Circus-specific stability, audience excitement, cast cohesion, prop condition, and supplies
- Deterministic show phases, Gloink population cycles, and faction influence
- Adventures construct persistent set pieces; crises damage them; character behavior changes
  shared social and environmental conditions
- Low stability, high audience pressure, and low cohesion feed back into character emotions
  and therefore later autonomous choices
- The observer scene renders the live NPC population and responds to system pressure

### Stage 18 - Advanced character psychology

- Persistent identity, personal history, ambition, subjective beliefs, internal conflicts,
  social status, reputation, behavioral habits, and private secrets
- Habits and standing evolve from validated actions and influence later decision scores
- Each circus character has a distinct psychological profile; secrets never enter public snapshots

### Stage 19 - Production presentation

- Animated show spotlights, portal motion, roaming Gloinks, confetti, and glitch transitions
- Browser-native ambient music and event sound effects with a persistent sound control
- Live world-system meters and public character reputation/habit cues
- Adaptive render scaling and hidden-tab suspension preserve browser performance

### Stage 20 - Episode system

- Daily Director incidents dynamically open episode-level stories
- Important characters, major event sequences, memorable moments, and outcomes accumulate
  from authoritative events instead of a fixed script
- Episodes close on resolution or day boundaries and persist in a durable world chronicle
- Major consequences remain available independently of the short live event feed

## Architecture

```text
Browser 3D observer <- WebSocket/snapshots <- FastAPI host
                                              |
                                      authoritative World <-> resilient persistence
                                              ^       |
                            validated Actions |       +-> psychology / world systems
                          +-------------------+-------------------+
                          |                                       |
                  Character agents                            Director
                  independent mock AI                 premises/circumstances only
                          +----------> AdventureManager <----------+
                                              |
                                      Episode chronicle
```

The mock provider selects among candidates generated from character state, goals,
memory, relationships, and perception. Provider output is still parsed as untrusted
structured data, so a future real provider can replace it without gaining direct
world access.

## Configuration

Defaults are safe and offline:

```text
AI_PROVIDER=mock
AI_MODEL=mock-v1
AI_API_KEY=
AI_TIMEOUT_SECONDS=2.0
```

See `.env.example`. Real provider adapters are intentionally outside this delivery;
selecting a non-mock provider produces a clear configuration error rather than
silently making network calls.

## Developer layout

- `models.py` - state, event, action, perception, and Director contracts
- `tools.py` - tool catalog and structured decision validation
- `ai.py` / `config.py` - asynchronous provider abstraction and offline mock
- `world.py` - authoritative validation, execution, perception, and environment
- `agents.py` - character reasoning pipeline and fallback behavior
- `memory.py` - tiered storage and relevance retrieval
- `relationships.py` - deterministic event-driven social projection
- `world_systems.py` - circus cycles, resources, NPC population, and shared pressures
- `episodes.py` - emergent episode assembly and persistent consequence chronicle
- `director.py` - summarized observation and cooldown interventions
- `adventures.py` - data-driven premises and event-triggered phase matching
- `persistence.py` - replaceable in-memory and atomic JSON repositories
- `simulation.py` - async scheduling, state projection, and snapshots
- `debug.py` - developer inspection without model reasoning traces
- `web_protocol.py` - observer-safe public JSON projection
- `web_server.py` - FastAPI host, WebSocket stream, autonomous loop, and autosave
- `web/` - procedural Babylon.js scene and observer dashboard

See [docs/STAGE_9_WEB_ARCHITECTURE.md](docs/STAGE_9_WEB_ARCHITECTURE.md) for the
browser boundary, [docs/STAGES_10_12_ARCHITECTURE.md](docs/STAGES_10_12_ARCHITECTURE.md)
for navigation/synchronization/voice, and
[docs/STAGES_13_15_ARCHITECTURE.md](docs/STAGES_13_15_ARCHITECTURE.md) for expression,
camera direction, and advanced story pacing, and
[docs/STAGES_16_20_ARCHITECTURE.md](docs/STAGES_16_20_ARCHITECTURE.md) for persistence,
world systems, psychology, presentation, and episodes.
