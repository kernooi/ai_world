# Autonomous AI World

A runnable, observer-only simulation implementing the project through
**Stage 12 - Voice**. Pomni, Ragatha, Jax, Gangle, Kinger, and Zooble
independently perceive a detailed digital circus,
reason from private state through a deterministic mock AI provider, submit
structured tool actions, experience authoritative consequences, remember events,
and develop directional relationships. Caine acts as the Director and introduces
validated circumstances and multi-step premises without choosing character behavior.
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

## Architecture

```text
Browser 3D observer <- WebSocket/snapshots <- FastAPI host
                                              |
                                      authoritative World <-> atomic persistence
                                              ^       |
                            validated Actions |       +-> private state projections
                          +-------------------+-------------------+
                          |                                       |
                  Character agents                            Director
                  independent mock AI                 premises/circumstances only
                          +----------> AdventureManager <----------+
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
- `director.py` - summarized observation and cooldown interventions
- `adventures.py` - data-driven premises and event-triggered phase matching
- `persistence.py` - replaceable in-memory and atomic JSON repositories
- `simulation.py` - async scheduling, state projection, and snapshots
- `debug.py` - developer inspection without model reasoning traces
- `web_protocol.py` - observer-safe public JSON projection
- `web_server.py` - FastAPI host, WebSocket stream, autonomous loop, and autosave
- `web/` - procedural Babylon.js scene and observer dashboard

See [docs/STAGE_9_WEB_ARCHITECTURE.md](docs/STAGE_9_WEB_ARCHITECTURE.md) for the
browser boundary and [docs/STAGES_10_12_ARCHITECTURE.md](docs/STAGES_10_12_ARCHITECTURE.md)
for navigation, resilient synchronization, and voice behavior.
