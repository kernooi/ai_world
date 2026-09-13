# Autonomous AI World — Master Project Context

## 1. Project Vision

Build a persistent 3D virtual world inspired by the concept of *The Amazing Digital Circus*, but as an original technical project.

The user is **only an observer**. The user must not directly control, command, influence, or interact with the characters during normal operation.

The world is inhabited by multiple genuinely autonomous AI characters. Each character has its own:

- personality
- goals
- motivations
- fears
- preferences
- memories
- emotional state
- relationships
- knowledge
- beliefs
- current intentions
- decision-making process

A separate higher-level **Director AI** oversees the world.

The Director AI creates situations, adventures, conflicts, discoveries, environmental events, and narrative opportunities. It should **not directly dictate every decision made by the characters**.

The desired experience is:

> The user watches a simulated world in which AI characters live, make decisions, form relationships, experience consequences, and create stories that were not explicitly scripted by the developer.

The ultimate goal is to create the feeling that the world is producing its own episodes.

---

## 2. Core Philosophy

This project must NOT simply be:

- scripted NPC dialogue
- a traditional game with AI voice lines
- a chatbot pretending to be a character
- a behavior tree with random dialogue
- a sequence of predefined quests
- an LLM generating a story that is then played back

Instead, the project should be a **live simulation**.

Core loop:

```text
WORLD EXISTS
    ↓
CHARACTERS PERCEIVE WORLD
    ↓
CHARACTERS FORM INTENTIONS
    ↓
CHARACTERS TAKE ACTIONS
    ↓
WORLD CHANGES
    ↓
CHARACTERS PERCEIVE CONSEQUENCES
    ↓
CHARACTERS UPDATE MEMORY / EMOTIONS / RELATIONSHIPS
    ↓
DIRECTOR OBSERVES THE WORLD
    ↓
DIRECTOR MAY INTRODUCE A NEW SITUATION
    ↓
CHARACTERS RESPOND AUTONOMOUSLY
    ↓
LOOP CONTINUES
```

The developer creates the **rules of the universe**, not the exact story.

---

## 3. User Role

The user is an observer.

There should be no standard gameplay controls for:

- moving characters
- choosing dialogue
- selecting quests
- telling characters what to do
- deciding outcomes
- controlling combat
- changing relationships
- forcing actions

The observer may eventually control presentation-related features such as:

- camera mode
- volume
- subtitles
- quality
- pause
- playback speed
- episode selection
- world reset

These controls must not influence character decisions.

Core rule:

> The user watches the world. The world does not obey the user.

---

## 4. High-Level Architecture

The system should be separated into major layers:

```text
                    OBSERVER
                       │
                       ▼
             ┌───────────────────┐
             │   PRESENTATION    │
             │   Camera / UI     │
             └─────────┬─────────┘
                       │
                       ▼
             ┌───────────────────┐
             │  UNREAL ENGINE    │
             │                   │
             │ Characters        │
             │ Environment       │
             │ Animation         │
             │ Physics           │
             │ Navigation        │
             │ Audio             │
             └─────────┬─────────┘
                       │
                 World Events
                       │
                       ▼
             ┌───────────────────┐
             │ WORLD SIMULATOR   │
             │                   │
             │ Time              │
             │ Weather           │
             │ Objects           │
             │ Locations         │
             │ Needs             │
             │ Rules             │
             │ Events            │
             └───────┬─────┬─────┘
                     │     │
            ┌────────┘     └────────┐
            ▼                       ▼
   ┌────────────────┐      ┌────────────────┐
   │ CHARACTER AI   │      │  DIRECTOR AI   │
   │                │      │                │
   │ Personality    │      │ Adventures     │
   │ Goals          │      │ Events         │
   │ Memory         │      │ Pacing         │
   │ Emotions       │      │ Escalation     │
   │ Relationships  │      │ Opportunities  │
   │ Decisions      │      │ World events   │
   └────────┬───────┘      └───────┬────────┘
            │                       │
            └──────────┬────────────┘
                       ▼
                 AI MODEL LAYER
```

---

## 5. Core Components

### 5.1 World Simulator

Responsible for the objective state of the universe.

Responsibilities:

- world time
- locations
- weather
- day/night
- physics-related state
- objects
- resources
- items
- doors
- environmental conditions
- characters' physical state
- events
- world rules
- persistent state

The LLM should NOT be the source of truth for world state.

Example:

```text
AI: "I want to walk to the cave."
        ↓
Action: move_to("cave")
        ↓
World simulator determines:
- cave exists
- path exists
- character can reach it
- action is allowed
```

The simulator is authoritative.

---

## 6. Character AI

Every major character should be an independent agent.

Example character profile:

```text
Character:
Alice

Personality:
- curious
- brave
- competitive
- emotionally expressive

Values:
- friendship
- freedom
- discovery

Primary goals:
- explore the world
- become respected

Secondary goals:
- protect friends

Fears:
- abandonment
- being powerless

Preferences:
- exploration
- dangerous challenges

Current emotional state:
- excited

Current location:
- village

Relationships:
- Bob: trusted friend
- Charlie: uncertain
- David: dislikes

Memories:
- Bob saved Alice previously
- Charlie lied once
- Alice discovered the cave
```

The character should reason using this information.

---

## 7. Character Decision Loop

Characters should not think every frame.

Use an event-driven / scheduled architecture.

```text
EVENT
  ↓
Character agent wakes
  ↓
Assemble perception
  ↓
Retrieve relevant memories
  ↓
Evaluate goals / emotions / relationships
  ↓
Consider possible actions
  ↓
LLM selects high-level intention
  ↓
Action sent to backend
  ↓
Action validated
  ↓
World executes action
  ↓
Result returned
  ↓
Character updates state / memory
```

The system should support asynchronous reasoning.

---

## 8. Character Perception

Characters must not automatically know everything in the world.

Each character receives limited, context-relevant perception.

Example:

```text
Location:
Forest

Visible:
- Alice
- river
- cave entrance
- broken cart

Audible:
- wind
- unknown noise near cave

Known:
- Bob went into the forest

Unknown:
- what is inside the cave
- what happened to the cart
```

Information asymmetry is essential.

---

## 9. Character Actions / Tools

Initial actions can include:

```text
move_to(location)
look_at(target)
talk_to(character)
inspect(object)
pick_up(object)
drop(object)
use_item(item)
open(object)
close(object)
eat(food)
drink(item)
sleep()
rest()
follow(character)
avoid(character)
attack(target)
defend()
run_to(location)
search(area)
```

More actions can be added later.

The LLM selects a high-level action. The simulation executes it.

---

## 10. Brain vs Body

Critical architectural rule:

> The LLM is the character's high-level brain. The browser renderer is the character's visual body and animation executor.

Example:

```text
AI:
"I want to investigate the cave."
        ↓
Action:
move_to("cave")
        ↓
Web renderer:
animate the validated route
        ↓
Character:
walks to cave
        ↓
World:
returns new observation
        ↓
AI:
decides next action
```

Do not use an LLM for:

- individual footsteps
- every frame
- exact animation timing
- low-level physics
- navigation
- collision
- frame-by-frame camera transforms

---

## 11. Character Memory

Characters need multiple memory levels.

### Short-Term Memory

Recent events:

```text
Bob told me not to enter the cave.
Alice entered the cave.
I just heard a monster.
I am currently injured.
```

### Long-Term Memory

Important historical experiences:

```text
Alice saved me during Adventure 2.
Bob betrayed me during Adventure 4.
Charlie helped me when I was injured.
```

### Semantic Knowledge

General knowledge:

```text
Fire is dangerous.
The village is north of the forest.
Bob is generally brave.
```

### Episodic Memory

Specific important events with emotional significance:

```text
Day 7
Bob abandoned Alice during the storm.
Emotional importance: high
```

Memories should have importance and relevance. Not every event should be stored permanently.

---

## 12. Relationships

Important character pairs should have dynamic relationship state.

Example:

```text
Alice → Bob

Trust: 72
Friendship: 81
Respect: 65
Fear: 5
Anger: 10
Suspicion: 12
```

Relationships evolve based on events.

Example:

```text
Bob lies to Alice.

Trust: 72 → 48
Suspicion: 12 → 37
Anger: 10 → 28
```

Relationships should emerge from experiences rather than being entirely hardcoded.

---

## 13. Personality

Personality should influence behavior while allowing variation.

Possible dimensions:

```text
Risk tolerance
Curiosity
Aggression
Empathy
Honesty
Confidence
Patience
Sociability
Independence
Competitiveness
Loyalty
Impulsiveness
```

Different characters should react differently to identical situations.

---

## 14. Goals and Motivations

Characters need goals beyond "follow the story."

Possible goals:

```text
Become powerful
Find treasure
Protect a friend
Understand the world
Become respected
Avoid death
Find a home
Become famous
Discover secrets
Avoid conflict
Prove themselves
```

Goals can conflict.

Example:

```text
Character wants:
- protect Bob
- become powerful

A dangerous artifact can make the character stronger,
but retrieving it may kill Bob.

The character must decide which goal matters more.
```

---

## 15. Emotional State

Characters should maintain emotional state such as:

```text
happiness
sadness
anger
fear
excitement
anxiety
curiosity
embarrassment
pride
loneliness
trust
```

Emotions modify priorities and decisions but do not replace reasoning.

---

## 16. Director AI

The Director is separate from the characters.

Primary responsibility:

> Create conditions in which interesting things can happen.

The Director should NOT constantly prescribe individual character actions.

Bad:

```text
Director:
Bob must betray Alice now.
```

Better:

```text
Director:
Create a situation where Bob has an opportunity
to gain something at Alice's expense.
```

Bob decides what to do.

---

## 17. Director Responsibilities

The Director may manage:

- adventure creation
- environmental events
- discovery opportunities
- conflicts
- escalating danger
- mysteries
- world expansion
- pacing
- dramatic tension
- transitions between phases
- major events

Example:

```text
World has become stagnant.

Director detects:
- characters are idle
- relationships are stable
- no major goals are progressing

Director creates:
A strange object appears in the forest.
```

---

## 18. Adventure Generation

Adventures should be high-level premises rather than rigid scripts.

Example:

```text
Adventure premise:
A strange signal is coming from an abandoned city.

Known:
The signal exists.

Unknown:
Who created it?

Unknown:
What happens if the characters investigate?

Unknown:
Will everyone cooperate?
```

Characters determine the resulting sequence of actions.

---

## 19. Event System

Support structured world events such as:

```text
Storm begins
Monster appears
Character becomes injured
Character discovers object
Character loses item
Door opens
Door locks
Character lies
Character helps another
Character insults another
Character enters location
Character leaves location
Treasure discovered
Environmental hazard triggered
```

Example event:

```json
{
  "event_type": "character_helped_character",
  "actor": "Alice",
  "target": "Bob",
  "location": "forest",
  "importance": 0.8
}
```

Events trigger relevant AI updates.

---

## 20. Event Bus

Use a centralized event bus.

```text
Browser observer
   ↓
Event Bus
   ↓
World State
   ↓
Character Agents
   ↓
Memory System
   ↓
Director
   ↓
Camera System
```

Only relevant agents should be activated where practical.

---

## 21. Camera AI

Eventually the camera should behave like a cinematographer.

It can consider:

- which character is currently important
- which event is interesting
- whether to follow action
- whether to establish the environment
- whether to switch viewpoints
- how to frame conversations

Example:

```text
Alice and Bob are talking.
Camera follows them.

Explosion occurs elsewhere.

Camera detects high-priority event.
Camera transitions toward explosion.

Characters react.
Camera follows whoever becomes most relevant.
```

The camera determines what the observer sees, not what happens.

---

## 22. Voice System

Later add voice generation / TTS.

Pipeline:

```text
Character decides dialogue
        ↓
Dialogue text
        ↓
Voice generation
        ↓
Audio
        ↓
Browser playback
```

Each character should have distinct:

- voice identity
- speaking style
- tone
- speaking speed
- emotional variation

Voice is a later-stage feature.

---

## 23. Facial and Body Animation

Eventually high-level emotional state should drive visual expression.

Examples:

```text
fear → nervous body language
anger → aggressive posture
joy → energetic movement
sadness → subdued movement
confusion → facial expression
```

LLM outputs high-level emotional/intent state. The web client maps it to animation.

---

## 24. Recommended Technology Stack

### 3D Presentation

**Babylon.js in the browser**

Responsibilities:

- 3D graphics
- world rendering
- animation
- navigation
- physics
- character movement
- environment
- audio
- camera
- visual effects

### Backend

**Python**

Responsibilities:

- agent orchestration
- world-state services
- AI calls
- memory
- event processing
- Director logic
- character state
- APIs

### Database

**PostgreSQL**

Stores:

- character profiles
- persistent memories
- relationships
- world data
- historical events
- episodes
- important state

### Fast State Layer

**Redis or equivalent**

Stores:

- current world state
- active events
- temporary agent state
- queues
- short-lived information

### Semantic Memory

Use a vector-enabled database or semantic retrieval mechanism for relevant memory retrieval.

### Communication

Use REST and WebSockets between the browser and the backend.

Conceptually:

```text
Browser
   ↕
WebSocket / API
   ↕
Python Backend
   ↕
AI / Database / Memory
```

---

## 25. AI Model Architecture

Do not hard-code the whole system to one AI model.

Use model interfaces so providers/models can be changed later.

Example abstraction:

```python
class AIModelProvider:
    async def generate(...):
        ...

    async def generate_structured(...):
        ...
```

Possible model roles:

- character reasoning model
- Director reasoning model
- lightweight summarization/classification/memory model

Prioritize:

- reasoning ability
- instruction following
- structured tool use
- latency
- cost
- context length
- reliability

---

## 26. Cost Management

Never call an LLM every frame.

### Level 1 — Game Engine

Handles:

```text
movement
animation
physics
navigation
collision
```

### Level 2 — Deterministic Simulation

Handles:

```text
hunger
stamina
weather
basic routine
simple reactions
```

### Level 3 — AI Reasoning

Handles:

```text
important decisions
social interactions
planning
uncertainty
conflicts
investigation
```

### Level 4 — Director Reasoning

Handles:

```text
major events
adventure generation
story pacing
world escalation
```

Use event-driven activation and asynchronous calls.

---

## 27. Persistence

The world should persist across sessions.

Store at minimum:

```text
Character memories
Relationships
Major discoveries
Important objects
Episode history
Character development
```

Example:

```text
Session 1:
Alice discovers a secret door.

Session ends.

Session 2:
Alice remembers the door.
Bob does not know about it unless Alice told him.
```

---

## 28. Information Asymmetry

Characters must have different knowledge.

Example:

```text
Alice knows:
The cave contains an artifact.

Bob does not know.

Charlie suspects:
Something is inside the cave.

Director knows:
There is an artifact.

Observer knows:
Whatever the camera currently reveals.
```

Characters must communicate to share knowledge.

---

## 29. Emergent Storytelling

Story should emerge from:

```text
Personality
+
Goals
+
Memories
+
Relationships
+
World conditions
+
Randomness
+
Director events
=
Emergent behavior
```

The exact sequence should not always be predictable.

---

## 30. Controlled Randomness

Randomness should create uncertainty without destroying coherence.

Bad:

```text
Randomly explode everything.
```

Better:

```text
Select plausible events based on:
- location
- current adventure phase
- world rules
- characters
- environment
- probability
- previous events
```

The Director uses randomness as a source of uncertainty, not chaos.

---

## 31. Agent Constraints

Characters operate within hard simulation constraints.

Examples:

```text
Cannot teleport.
Cannot know hidden information.
Cannot perform impossible actions.
Cannot modify world rules.
Cannot access backend internals.
Cannot directly control another character.
Cannot see information outside perception.
```

The AI operates inside the simulation, not above it.

---

## 32. Structured AI Output

The AI should return structured outputs for decisions.

Example:

```json
{
  "intent": "investigate_cave",
  "target": "cave_01",
  "priority": 0.82,
  "reason": "The unusual sound may be related to the missing artifact.",
  "emotional_state": {
    "fear": 0.32,
    "curiosity": 0.87
  }
}
```

Backend validates outputs using schemas.

Never allow raw model output to directly mutate critical world state.

---

## 33. Action Validation

Every AI action passes through validation.

Example:

```text
AI:
move_to("castle")
        ↓
Validator:
- Does castle exist?
- Is it reachable?
- Is character alive?
- Is action currently possible?
        ↓
Valid:
execute

Invalid:
return failure to AI
```

The world simulator remains authoritative.

---

## 34. Simulation Loop

Conceptually:

```text
Every simulation cycle:

1. Update world
2. Process events
3. Update character state
4. Determine which agents need reasoning
5. Run relevant character decisions
6. Validate actions
7. Execute actions
8. Generate resulting events
9. Update memory
10. Update Director
11. Update camera
12. Save important state
```

AI reasoning should be asynchronous and must not block the whole simulation.

---

## 35. Asynchronous Architecture

Use async tasks and queues.

```text
World Event
    ↓
Event Queue
    ↓
Character A reasoning task
Character B reasoning task
Director reasoning task
    ↓
Actions queued
    ↓
World execution
```

One slow agent must not freeze the simulation.

---

## 36. Observability and Debugging

Create developer/debug tools.

Example character inspector:

```text
Character:
Alice

Current goal:
Protect Bob

Current emotion:
Fear = 0.42
Curiosity = 0.79

Current intention:
Investigate cave

Relevant memories:
1. Bob saved Alice
2. Cave was previously unexplored

Relationship:
Bob trust = 82

Last action:
Move to cave

Reasoning status:
Waiting for world result
```

Also provide:

- event log
- AI call log
- token/usage metrics
- latency metrics
- world-state inspector
- memory inspector
- relationship inspector
- Director state
- camera state

Observability is a first-class feature.

---

## 37. Testing Strategy

Test:

### World simulation

- movement
- items
- doors
- locations
- weather
- time

### Character systems

- memory
- relationships
- goals
- emotions
- perception
- action validation

### Agent system

- structured output
- tool calls
- invalid actions
- timeouts
- retries
- model failures

### Director

- event generation
- pacing
- constraints

### Integration

- Browser ↔ backend
- event synchronization
- action execution
- state persistence

Also create scenario tests.

Example:

```text
Given:
Alice trusts Bob.

When:
Bob helps Alice.

Then:
Alice's trust should not decrease.
```

---

## 38. Failure Handling

Expect:

- LLM timeout
- invalid JSON
- invalid action
- hallucinated object
- duplicate action
- contradictory action
- provider unavailable
- database error
- network failure

Backend should:

```text
validate
retry when appropriate
fallback when appropriate
log errors
preserve world consistency
```

A failed AI request must not destroy the simulation.

---

# 39. Full Development Roadmap

## STAGE 0 — Project Foundation

Goal: establish clean architecture.

Set up:

```text
Git
Python
environment configuration
logging
testing
project structure
configuration management
AI provider abstraction
database abstraction
```

Expected result: a runnable backend with basic services.

---

## STAGE 1 — Pure Text World

No 3D presentation yet.

Create a tiny Python world.

Example world:

```text
Village
Forest
Cave
River
```

Characters:

```text
Alice
Bob
Charlie
```

Director:

```text
Director AI
```

Basic actions:

```text
move
talk
inspect
rest
explore
```

Goal:

> Characters behave autonomously in a text environment.

---

## STAGE 2 — Character Brains

Implement:

```text
personality
goals
memory
relationships
emotions
perception
decision-making
```

Important milestone:

> The developer should be able to observe decisions that were not explicitly scripted.

---

## STAGE 3 — Tool-Based Agents

Implement action/tool framework:

```text
move_to
talk_to
inspect
pick_up
drop
search
eat
sleep
```

Flow:

```text
LLM selects tool
→ backend validates
→ world executes
→ result returned to agent
```

---

## STAGE 4 — Persistent Memory

Implement:

```text
short-term memory
long-term memory
episodic memory
semantic retrieval
memory importance
memory summarization
```

Test cross-session memory.

---

## STAGE 5 — Relationships

Implement dynamic social state.

Characters remember:

```text
who helped them
who betrayed them
who lied
who they trust
who they dislike
```

Relationships evolve from events.

---

## STAGE 6 — World Simulation

Add:

```text
time
day/night
weather
needs
health
resources
items
environmental events
```

The world becomes partially autonomous and persistent.

---

## STAGE 7 — Director AI

Introduce Director.

Start with simple events:

```text
Storm incoming.
Strange object appears.
Animal disappears.
New location becomes accessible.
```

Do not initially build complicated narrative generation.

---

## STAGE 8 — Emergent Adventures

Allow multi-step situations.

Example:

```text
Mysterious signal detected.
Characters investigate.
They discover a hidden location.
They disagree about entering.
Someone enters alone.
Something happens.
Other characters react.
```

The outcome comes from character decisions.

---

## STAGE 9 — Browser 3D Integration

Connect the Python backend to a browser-native Babylon.js presentation through FastAPI.

The active theme is a detailed indoor digital circus. Start with:

```text
striped main circus tent
center stage, bedroom hall, dining hall, and backstage props
adventure portal
Pomni, Ragatha, Jax, Gangle, Kinger, and Zooble
Caine as the Director
```

Python simulation remains authoritative for AI state.

The web client procedurally creates the environment and character bodies, then visualizes
validated movement, actions, dialogue, adventures, time, and weather. No manual 3D modelling
or engine editor work is required.

Provide a one-click launcher, automatic browser opening, autosave, reconnect snapshots,
and observer-only pause/playback-speed controls.

Caine creates at most one event per in-world day. He creates conditions and adventures,
never character actions or predetermined outcomes.

---

## STAGE 10 — Rich Navigation and Character Bodies

Implement:

```text
route interpolation
movement transitions
procedural pathfinding
interaction
collision
basic animation
```

The browser uses reversible waypoint routes around rings and props, stable per-character
lane offsets, collision-enabled meshes, independently animated limbs, and distinct
motions for conversation, helping, searching, objects, rest, and sleep.

Example:

```text
AI:
move_to(adventure_portal)

Browser:
character follows a clear multi-point route to the portal
```

---

## STAGE 11 — Real-Time Synchronization

Build robust backend ↔ browser communication.

Synchronize:

```text
character location
movement
actions
events
animations
world state
```

Make communication asynchronous.

Use versioned envelopes, session and message IDs, acknowledgements, duplicate suppression,
a bounded replay buffer, heartbeat monitoring, and full-snapshot fallback. Reconnects must
never invent, reorder, or silently lose authoritative events.

---

## STAGE 12 — Voice

Add:

```text
TTS
voice identity
emotion
speech timing
dialogue playback
```

Use browser-native speech synthesis for the mock-AI phase. Give every character and Caine
a distinct voice profile, modify pitch and timing from public emotion state, synchronize
captions and body motion to speech, and provide persistent volume/mute controls. Do not
require a cloud TTS account or voice-cloning asset.

---

## STAGE 13 — Facial Animation and Expressiveness

Add:

```text
facial expressions
body language
gesture selection
emotion-driven animation
```

Expose procedural face controls for eyes, brows, mouth, blink, and head angle. Blend
dominant emotion into facial pose and body posture while allowing validated actions and
speech to select temporary gestures.

---

## STAGE 14 — Camera AI

Build cinematic camera behavior:

```text
following important characters
detecting interesting events
switching scenes
choosing viewpoints
framing conversations
showing environmental events
```

Score authoritative events by visual interest. Use eased close, medium, wide,
conversation, follow, establishing, and Caine announcement shots. Manual observer input
temporarily overrides the camera AI and never affects world state.

---

## STAGE 15 — Advanced Director

Expand Director to manage:

```text
story pacing
adventure arcs
tension
mysteries
character development opportunities
world expansion
major events
```

Preserve character autonomy.

Persist a compact pacing model containing tension, arc stage, quiet time, focus character,
development opportunity, major-event count, and world expansion. Derive pacing from
adventure phase, public emotion, activity, and relationship tension. Offer personal
development circumstances, multi-day adventure arcs, major events, and validated new
paths while retaining Caine's once-per-day limit and total inability to issue character actions.

---

## STAGE 16 — Persistent World

Continue the world across sessions.

Persist:

```text
character history
memories
relationships
discoveries
locations
objects
major consequences
```

Implemented with versioned full-state JSON, atomic replacement, last-known-good backup
recovery, and forward migration of existing circus saves. The save includes private
memory and psychology, the complete event history, mutable geography and objects,
world-system state, the episode chronicle, and durable major consequences.

---

## STAGE 17 — Advanced World Simulation

Potential systems:

```text
economy
resource systems
NPC populations
animals
environmental cycles
factions
settlements
construction
destruction
political/social systems
```

Only add systems that create meaningful emergent behavior.

Implemented circus-specific systems: digital stability, audience excitement, cast
cohesion, prop condition, food supply, deterministic show/environment cycles, Gloink
NPC population, cast/Caine/Gloink influence, and persistent constructed or damaged set
pieces. These systems react only to authoritative events and are visible in the browser.

---

## STAGE 18 — Advanced Character Psychology

Expand agents with:

```text
beliefs
values
identity
personal history
long-term ambitions
internal conflicts
social status
reputation
habits
preferences
secrets
```

Implemented as persistent per-character psychology. Repeated validated choices reinforce
habits; helping and deception change reputation and social status; received statements
form confidence-weighted subjective beliefs. Psychology influences decision scoring and
provider context, while secrets remain private and never appear in observer snapshots.

---

## STAGE 19 — Production Presentation

Improve:

```text
3D models
lighting
VFX
sound effects
music
facial animation
voice quality
environment detail
camera transitions
UI
performance
```

Implemented with procedural character rigs and expressions, show spotlights, animated
portals and Gloinks, confetti and glitch VFX, browser-native ambient music and event
sounds, speech synthesis, cinematic easing, system-rich UI, adaptive render scaling,
and hidden-tab render suspension. No external 3D or audio production assets are required.

---

## STAGE 20 — Episode System

Create episode-level concepts.

Example:

```text
Episode 1:
The Door

Episode 2:
The Forest

Episode 3:
The Missing Artifact
```

Episodes may emerge dynamically instead of being fully prewritten.

Store:

```text
episode premise
major events
important characters
key outcomes
memorable moments
```

Implemented as an event-driven, persistent chronicle. Director incidents open episodes;
authoritative events select important characters, major sequences, and memorable moments;
adventure resolution or a world-day boundary closes the episode with accumulated outcomes.
The episode list and major consequences are exposed to the observer without private state.

---

# 40. MVP Definition

Minimum viable version:

```text
3 AI characters
1 Director AI
1 small world
3-5 locations
memory
personality
goals
relationships
basic emotions
basic actions
event system
simple persistence
text output
```

No high-quality graphics required.

Success criterion:

> Characters make believable decisions independently and produce interactions without the developer scripting the exact sequence.

---

# 41. First Visual Prototype

After MVP:

```text
3 AI characters
small 3D environment
basic animation
basic movement
basic dialogue
Director events
persistent memories
```

The user simply watches.

Success criterion:

> It feels like watching characters live inside a small world rather than playing a conventional game.

---

# 42. Long-Term Final Product

Ideal flow:

```text
Launch application
        ↓
Enter virtual world
        ↓
Characters already have histories
        ↓
Director begins / continues an adventure
        ↓
Characters interact
        ↓
Unexpected events happen
        ↓
Characters make independent choices
        ↓
Relationships evolve
        ↓
Consequences accumulate
        ↓
Camera follows important events
        ↓
Characters speak and emote
        ↓
Adventure reaches a conclusion
        ↓
World continues
        ↓
Next episode emerges
```

The user remains an observer.

---

# 43. Example Final Scenario

Initial world state:

```text
Alice
Bob
Charlie
David
```

Relationships:

```text
Alice trusts Bob.
David distrusts Bob.
Charlie is cautious.
Bob wants to become rich.
```

Director event:

```text
A mysterious treasure map appears.
```

Possible emergence:

```text
Bob wants the treasure.
Alice wants to help Bob.
David suspects the map is a trap.
Charlie does not want to go.
Bob convinces Alice to follow him.
David follows them because he does not trust Bob.
Charlie changes his mind after discovering evidence.
The group enters an abandoned structure.
Bob finds treasure.
The treasure causes a dangerous event.
Alice tries to save Bob.
David must decide whether to help.
Charlie panics.
```

No rigid scene-by-scene script should determine the result.

The resulting experiences become persistent memories.

---

# 44. Success Criteria

The project is successful when:

### Characters feel different

Alice and Bob should not behave identically.

### Characters remember

Past events affect future decisions.

### Characters have limited knowledge

They only know what they perceived or learned.

### Relationships persist

Friendships and conflicts evolve.

### Characters surprise the developer

The exact sequence is not always predictable.

### Director avoids puppeteering

Director creates situations rather than controlling every character action.

### World has consequences

Actions affect future state.

### User is genuinely an observer

The user does not secretly control outcomes.

### World persists

Episodes influence future episodes.

### Visual presentation communicates AI state

Emotions and events should eventually be understandable through animation, camera, voice, and environment.

---

# 45. What NOT to Build First

Do not begin with:

```text
photorealistic graphics
20+ characters
massive open world
complex combat
full voice acting
advanced facial animation
multiplayer
VR
huge procedural environments
```

Start with:

```text
3 autonomous characters
1 Director
1 tiny world
memory
relationships
goals
personality
events
```

If the AI system is not interesting in text, better graphics will not fix it.

---

# 46. Recommended Repository Structure

```text
autonomous-ai-world/
│
├── backend/
│   ├── agents/
│   │   ├── character_agent.py
│   │   ├── director_agent.py
│   │   └── camera_agent.py
│   │
│   ├── world/
│   │   ├── world_state.py
│   │   ├── event_bus.py
│   │   ├── locations.py
│   │   ├── objects.py
│   │   └── simulation.py
│   │
│   ├── memory/
│   │   ├── short_term.py
│   │   ├── long_term.py
│   │   ├── retrieval.py
│   │   └── summarization.py
│   │
│   ├── relationships/
│   │   └── relationship_manager.py
│   │
│   ├── models/
│   │   ├── character.py
│   │   ├── world.py
│   │   ├── event.py
│   │   └── actions.py
│   │
│   ├── ai/
│   │   ├── provider.py
│   │   ├── prompts.py
│   │   └── schemas.py
│   │
│   ├── api/
│   │   └── server.py
│   │
│   └── tests/
│
├── unreal/
│   └── AutonomousWorld/
│
├── database/
├── docs/
├── scripts/
├── .env.example
├── README.md
└── pyproject.toml
```

The structure can evolve as complexity increases.

---

# 47. Codex Development Rules

Codex should act as the senior software engineer for this project.

Do not ask Codex to implement the entire final system in one attempt.

For each stage:

```text
1. Inspect the existing repository.
2. Understand the current architecture.
3. Identify dependencies and constraints.
4. Design the change.
5. Implement the change.
6. Run tests.
7. Fix errors.
8. Update documentation.
9. Explain significant architectural decisions.
10. Preserve previous functionality.
```

When adding a subsystem:

```text
design interface
→ implement
→ test
→ integrate
```

Prefer small, reviewable changes over massive rewrites.

---

# 48. Non-Negotiable Architectural Principles

1. The world simulator is authoritative.
2. AI agents cannot directly mutate critical world state.
3. All AI actions are structured and validated.
4. Character knowledge is limited by perception and communication.
5. Character memories persist appropriately.
6. Relationships evolve from events.
7. Personalities influence decisions.
8. Goals can conflict.
9. The Director creates conditions, not predetermined behavior.
10. The user is an observer.
11. Low-level movement and animation are handled by the browser renderer.
12. LLM reasoning is high-level and event-driven.
13. AI calls are asynchronous.
14. The system must survive AI/network/model failures.
15. AI provider/model interfaces must remain replaceable.
16. Automated tests are required for core subsystems.
17. Debugging and observability are first-class concerns.
18. Build text simulation before 3D integration.
19. Keep the world persistent and stateful.
20. Favor emergent behavior over scripted outcomes.

---

# 49. Initial Codex Instruction

Use this as the initial instruction after the repository is created:

> You are the senior software engineer helping build an autonomous AI world simulation.
>
> The project contains multiple AI characters living inside a persistent simulated environment.
>
> Each character must have independent personality, goals, memory, emotions, relationships, limited perception, beliefs, and decision-making.
>
> A separate Director AI creates situations and adventures but must not directly control individual character decisions.
>
> The user is an observer and cannot directly control or interact with the characters during normal operation.
>
> The final system will have a browser-native 3D representation, while the AI simulation and orchestration remain independently implemented in Python.
>
> Build the project incrementally, beginning with a small text-based simulation before introducing browser 3D.
>
> Treat the world simulator as authoritative.
>
> Treat LLMs as high-level reasoning systems, not physics engines, navigation systems, or frame-by-frame controllers.
>
> All AI actions must be structured and validated.
>
> Characters must have limited knowledge and persistent memories.
>
> The system should support emergent stories rather than predefined scripts.
>
> The ultimate goal is an experience where the user watches autonomous AI characters generate their own adventures inside a persistent 3D world.
>
> Never implement the entire final system in one step. Begin with Stage 0 and Stage 1, keep the architecture modular, write tests, and ensure every stage remains runnable before proceeding.

---

# 50. Final Definition

This project is an **autonomous AI-driven persistent virtual world**.

It is not primarily a game, chatbot, or animation. It is a simulation populated by autonomous artificial characters.

The 3D environment is the visual/physical body of the simulation.

The world simulator defines its rules.

The character agents are its inhabitants.

Memory provides continuity.

Relationships provide social dynamics.

The Director provides situations and narrative pressure.

The camera presents important events to the observer.

The AI characters make the decisions.

The developer defines the universe's rules and constraints.

The observer watches.

The ultimate objective is to reach a point where the developer can start the system, leave it running, and observe a sequence of interactions and adventures that were **not explicitly written beforehand**, while still remaining believable, coherent, persistent, and constrained by the world's rules.

The most important success test is:

> **Can the world produce an interesting event that the developer did not explicitly script, caused by the interaction of autonomous characters, their memories, goals, personalities, and the Director's environmental decisions?**

If yes, the project has achieved its core objective.
