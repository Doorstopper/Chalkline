# Task: chalkline-clip-timeline
## Objective
Review the proposed first native clip timeline packet for time-coordinate and data-preservation risks.
## Scope
Only desktop/src/chalkline/domain/timeline.py, desktop/src/chalkline/domain/timing_edits.py, and Studio.setTrim / updateTiming / selectClip in desktop/src/chalkline/application/studio.py. Atlas is implementing new timeline code independently.
## What to produce
At most 200 words of actionable checks. Design: source-time clip strip with separate trim, freeze, slow and markup lanes. Clicking seeks. Start/end handles capture the displayed scale on press and commit one undoable edit on release, clamped to source bounds and retaining the tag moment. Keep absolute annotation times and unknown fields unchanged. Show timing markers and open existing timing dialogs; moving freezes/slow regions is a later packet. Cancel stale edits after selection/document changes. Related controls and source helpers will be grouped together.
## Evidence required
Cite the exact source paths/lines for each risk. Distinguish checked source from assumptions; do not claim tests ran.
## Out of scope
No file edits, commands, other files, delegation, deployment, or complete PWA inventory. Do not propose dropping functions.
