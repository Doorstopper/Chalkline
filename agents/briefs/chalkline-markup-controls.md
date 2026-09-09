# Task: chalkline-markup-controls
## Objective
Read-only review of markup editing risks for the next native packet.
## Scope
Read desktop/src/chalkline/rendering/annotations.py and domain/project.py, plus Studio checkpoint, touchCurrent, selectClip and stopReview in application/studio.py. No inventory redo.
## What to produce
At most 200 words of actionable source-backed checks. Codex is independently implementing seven already-rendered tools, transient drag creation, selected-shape colour/text/timing edits, duplicate/delete and normalized movement. Keep unknown fields, original source times, one undo step per gesture; cancel stale drags after document/clip changes. Global line thickness uses session.lineWt. Existing unsupported geometry still blocks export.
## Evidence required
Exact paths/lines for claims. Identify risks rather than claim tests ran.
## Out of scope
No writes, commands, other files, deployment or feature removal.
