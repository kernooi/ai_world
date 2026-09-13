# Stages 10–12: Movement, Synchronization, and Voice

## Stage 10 — Rich navigation and character bodies

The Python `World` remains the authority for whether a move is legal. Once a validated
`moved` event reaches the browser, the renderer resolves the location pair through a
procedural route table. A route contains clear interior waypoints around rings, seating,
the stage, and props. Routes work in both directions, and a stable per-character lane
offset prevents six characters from occupying the same visual line.

Babylon animation keys interpolate along the complete route. Limb cycles run only while
the route is active. Other authoritative events select short body motions: conversational
gestures, helping, looking around, reaching for an object, resting, and sleeping. Visual
collision metadata is enabled on character meshes and the scene, while logical collision
and destination legality remain backend responsibilities.

## Stage 11 — Real-time synchronization

Every WebSocket message has this envelope:

```json
{
  "protocol_version": 1,
  "session_id": "server-session-id",
  "message_id": 42,
  "server_time": "2026-09-13T12:00:00+00:00",
  "type": "tick"
}
```

The browser acknowledges applied message IDs, ignores duplicates, and monitors a
five-second heartbeat. A reconnect supplies its session and last applied message ID.
If those messages remain in the 256-entry replay buffer, the server sends them in order;
otherwise it sends a complete public snapshot. Full tick snapshots make every applied
tick a valid synchronization checkpoint. A server restart changes `session_id`, forcing
a clean snapshot rather than mixing states from two processes.

Inbound traffic remains observer-only. The protocol accepts acknowledgements plus pause
and playback speed. It does not accept actions, destinations, dialogue, Director events,
or world mutations.

## Stage 12 — Voice

Dialogue uses the browser's installed Web Speech voices. Every character and Caine has a
separate profile containing voice-name preferences, pitch, and speaking rate. Current
emotion modifies those parameters within safe browser ranges: anxiety accelerates,
fear slows and raises pitch, anger lowers pitch, and happiness or excitement adds energy.

The native speech queue preserves dialogue order. Speech start/end callbacks drive the
speaker's body timing, while captions remain visible for a duration derived from text
length. Caine voices validated daily adventures and environment announcements. Voice
enablement and volume are stored locally in the browser. No text, voice sample, or audio
is sent to an external TTS provider by this application.
