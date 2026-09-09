# Task: chalkline-timing-drag-proposal
## Objective
Provide a response-only Python implementation proposal for a pure domain helper.
## Scope
Read only desktop/src/chalkline/domain/timing_edits.py, domain/clip_timeline.py,
domain/timeline.py, and index.html lines 3217-3232 and 3289-3305. Do not edit files.
## What to produce
At most 100 lines of Python plus 100 words of explanation. Propose
drag_timing(mark, kind, index, edge, source_time, offset, duration) returning a
deep-copied mark. kind is freezes (edge at) or slow (edge from/to). Source-time
coordinates, 0.1s snap then clamp to clip bounds, slow ends must not cross and
must retain at least 0.1s. Retain the other slow endpoint, rate, freeze hold,
all annotation times/keyframes, unknown fields, array order and the legacy
single-dictionary slow representation. Validate stale indices and nonfinite
input. No manual freeze is added for an automatic drawing beat. Preserve raw
list indices; no sorting/merging. Return errors for impossible intervals.
## Evidence required
Refer to exact source lines for snapping, bounds and source-time behavior.
## Out of scope
No edits, commands, delegation, dependencies, deployment or inventory. Cite the
source supporting timing semantics. Codex handles transactions, UI and tests.
