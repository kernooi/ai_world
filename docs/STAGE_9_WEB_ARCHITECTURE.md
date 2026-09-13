# Stage 9: Browser-Native 3D World

Stage 9 replaces the planned Unreal integration with a zero-authoring web presentation.
The existing Python simulation remains authoritative. The browser never decides an
action or mutates world state; it projects public state into a procedural Babylon.js
scene and observer dashboard.

## Runtime boundary

```text
Character AI / Director
          |
   validated actions
          v
Authoritative Python World ----> atomic JSON autosave
          |
  public state projection
          v
FastAPI snapshot + WebSocket
          |
          v
Babylon.js renderer + observer UI
```

`GET /api/snapshot` returns a complete reconnectable public view. `WS /ws` sends an
initial `snapshot`, a `control_state`, and then one `tick` message containing the
new public state plus ordered events for animation. Sequence numbers let the UI retain
the authoritative event ordering.

The public projection deliberately excludes private memories, undiscovered objects,
private knowledge, full relationship state, provider prompts, and reasoning internals.

## Observer controls

The only accepted inbound message is:

```json
{"type":"observer_control","control":"paused","value":true}
```

`control` can be `paused`, or `speed` with `0.5`, `1`, `2`, or `4`. These alter
presentation pacing only. Character actions, locations, goals, outcomes, and Director
events cannot be supplied by the browser.

## Circus scenario

The active web scenario contains Pomni, Ragatha, Jax, Gangle, Kinger, and Zooble as
six independent agents with different goals, fears, values, emotions, and social
tendencies. Caine is the Director. His daily cadence is keyed to `WorldTime.day`, so
he can introduce no more than one validated circumstance or adventure per calendar
day. He creates the setup; the six character agents decide what to do with it.

An old pre-circus browser save is detected by its cast and replaced with the circus
scenario on startup. The original is first preserved beside it as
`world_state.pre-circus.json`. Circus saves continue normally across later launches.

## Procedural presentation

All current visual content is assembled in code: the striped interior shell, checkerboard
floor, three circus rings, gold supports, marquee bulbs, trapeze, bleachers, stage,
curtains, bedroom hall, banquet table, backstage props, rainbow portal, Caine, and six
distinct character bodies. Existing world events drive travel animation, dialogue
bubbles, activity pulses, adventure highlights, lighting, fog, and digital rain. There
are no FBX/GLTF assets and no modelling workflow.

## Operation and recovery

`start_world.bat` creates `.venv`, installs the package, starts the local server, and
opens the browser. The host binds to `127.0.0.1` by default, so it is not exposed to the
local network. State is atomically saved after every tick and on graceful shutdown to
`.runtime/world_state.json`. A disconnected browser retries with exponential backoff and
receives a fresh snapshot on reconnect.

Developer options:

```powershell
ai-world-web --port 9000 --tick-seconds 1.5
ai-world-web --fresh --seed 12
ai-world-web --no-browser
```
