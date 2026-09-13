# Autonomous AI World

A runnable, observer-only Python simulation implementing the project through
**Stage 8 - Emergent Adventures**. Three independent characters perceive a small world,
reason from private state through a deterministic mock AI provider, submit
structured tool actions, experience authoritative consequences, remember events,
and develop directional relationships. A separate Director periodically introduces
validated circumstances and multi-step premises without choosing character behavior.

No API key, network service, database server, or Unreal Engine is required.

## Run

Python 3.11 or newer is required.

```powershell
python -m pip install -e ".[dev]"
ai-world --steps 12 --seed 7
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

## Architecture

```text
Observer CLI <- debug/event views <- authoritative World <- persistence repository
                                        ^       |
                                        |       +-> event projection
                      validated Actions |             |-> private memory/knowledge
                                        |             |-> emotion/relationships
                          +-------------+-------------+
                          |                           |
                  Character agents                Director
                  independent mock AI       compact summary + mock AI
                  local perceptions         premises/circumstances only
                          |                           |
                          +----> AdventureManager <--+
                                 event-triggered phases
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

See [docs/STAGE_8_ARCHITECTURE.md](docs/STAGE_8_ARCHITECTURE.md) for adventure
invariants, lifecycle rules, and acceptance boundaries. The Stage 7 document remains
as the previous architecture milestone.
