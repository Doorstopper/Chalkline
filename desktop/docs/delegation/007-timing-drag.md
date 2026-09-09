# Task 007 — manual freeze and slow edge dragging

The user requested another packet after asking whether Fable and Opus were being
used. Both received bounded tasks through the existing read-only Atlas profile.
No agent was granted write access to the shared uncommitted source tree.

Opus/Bolt task `chalkline-timing-drag-proposal` returned a pure domain helper.
Codex checked its cited PWA behavior and integrated it into timing_edits.py.
It deep-copies the clip, snaps absolute source time to tenths, clamps to clip
bounds, prevents slow edges crossing, and preserves array order, legacy single
slow dictionaries, rates, holds, drawings/keyframes and all unknown fields.
Manual freeze dragging intentionally does not move associated drawing times,
matching index.html moveFreezeDrag. This can leave an automatic drawing freeze
at the original time as well as the moved manual freeze.

The existing application/clip_timeline.py transaction owns both source trim and
timing drags. QML TimelineTimingSurface.qml is a stable pointer owner above the
changing marker delegates. Press captures context/scale; motion previews only;
release commits once. Clicks without movement and cancelled interactions leave
no history entries. Manual points remain individually represented even when
the playback planner merges their holds. Automatic drawing beats are read-only
hints. Slow bars expose two visible edge grips; body click seeks and double-click
opens the existing numeric editor. Double-clicking a drawing marker selects it
in the grouped markup panel.

103 native tests and QML startup passed, including 11 new domain/QML tests.
These cover real pointer capture while marker models rebuild, multiple moves,
crossing another freeze, both slow grips, no-op imported times, legacy dictionary
round trips, one-step undo, Escape, selection/document/edit/export invalidation
and actual double-click dispatch. No export renderer/planner algorithm changed.

Fable/Lens task `chalkline-timing-drag-review` stopped at its configured $1
estimated per-run budget, reporting budget_exhausted with $1.2815 total estimated
usage. No review findings were returned or accepted. It was not retried. Opus
reported $0.2481 estimated usage. These are CLI estimates, not subscription
quota percentages or billed charges. Lead code review and tests were completed;
an independent completed review is still absent.

The E:/Chalkline folder then became unavailable. A newly added short media proof
(`verify_media.py --markup --timing-drag`, expected 5.4 s at source 4K) could not
launch, and no new preview could be opened. A clarification about the drive was
sent to the user. Restore that folder (or confirm its replacement location), run
the new proof, inspect the handles, then record Opus acceptance through Atlas.
Do not mark the failed Lens run accepted. Do not rerun tests already passed
unless source changes or another concrete concern justifies it.

Live PWA files, installed binaries and saved user projects were not modified.
Source remains uncommitted; no push, deployment or packaging was performed.
