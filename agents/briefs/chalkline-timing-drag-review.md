# Task: chalkline-timing-drag-review
## Objective
Review the integrated native freeze/slow timing-drag packet, including Opus's helper.
## Scope
Read only desktop/src/chalkline/domain/timing_edits.py, domain/clip_timeline.py,
application/clip_timeline.py, ui/TimelineTimingSurface.qml and ui/ClipTimeline.qml.
## What to produce
At most 250 words of actionable defects and edge-case checks, with source lines.
Focus on stable pointer ownership while QML marker delegates rebuild, drag
cancellation, raw timing indices/order, no-op clicks/double-click, stale
clip/project state, non-crossing slow edges and legacy dictionary preservation.
Manual freeze dragging must leave all drawing times unchanged. Automatic drawing
freeze hints are read-only; existing double-click editing may add a manual freeze.
Codex owns implementation and tests. Do not invent feature removals.
## Evidence required
Inspect the actual source; distinguish confirmed problems from possible checks.
Do not claim tests ran. Refer to exact file locations.
## Out of scope
No writes, commands, additional files, delegation, dependencies or deployment.
