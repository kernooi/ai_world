# Circus visual and locomotion overhaul

The browser now uses `circus-art.js` for original procedural character rigs and
theatrical scenery, and `navigation.js` for spatial navigation. No modeling tool,
paid asset pack, AI API key, or Unreal installation is needed. Babylon.js still
loads from its CDN, so the first page load requires internet access.

## Presentation

The six cast members have distinct silhouettes, faces, clothing, hands and
accessories. Caine has a complete ringmaster body and tooth-lined jaw. Joint-based
walking, knee bends, head motion, blinks, speech mouths and short-lived gestures
replace indefinitely looping action animations. The art is a procedural
interpretation, not the show's production models or an exact visual match.

The rectangular circus interior includes pleated curtains, gilded columns,
overhead ribs and lights, trapeze, stage, audience seating and floor inlays.
Bedroom doors, dining furniture and cake, backstage props, fountains, trees,
rides, lake, theater and portal scenery distinguish the wider campus. Adventure
locations retain their themed island scenery.

Use **The grounds** for an overview, **Follow cast** or a character card for a
close view, and **Cinema view** to hide panels. Drag to orbit and scroll to zoom.

## Movement boundary

The browser picks varied floor destinations within a location, uses A* and
line-of-sight smoothing around inflated scenery footprints, steers with
acceleration and neighbor separation, and roams during idle time. There are no
fixed painted routes or prescribed waypoint lists. Blocked steering replans.
Cross-world travel uses a short portal transition, not walking through the void.

This is **client-side spatial presentation**. Python remains authoritative for
semantic room/location decisions, quests, items and social actions. Physical
positions are not yet persisted, synchronized across observers or used to
validate reach distance for interactions. Mock AI is unchanged; this overhaul
does not eliminate repetitive mock dialogue or add learned spatial reasoning.

## Verification and performance

Run `python -m pytest -q` and `node --test tests/web_navigation.test.cjs`.
Navigation tests exercise clear-floor routing, obstacle detours, corner clearance,
fractional starting positions, unreachable barriers, pocket-world boundaries and
spawn recovery. Chrome rendering and cast positions were inspected directly.
An integrated browser steering check traversed around the raised stage, stayed
on clear floor throughout and stopped within 0.18 units of its destination.

Static scenery is batched by material; shadow quality and render resolution adapt
to frame rate. Hardware-accelerated WebGL is recommended. Software-rendered
headless Chrome was slow even with batching; a smooth GPU frame rate has not been
established by that test. This is not a production performance benchmark.
