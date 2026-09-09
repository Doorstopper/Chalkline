# Task 006 — markup controls and viewable preview

Codex implemented the next bounded packet at the user's request. Atlas Scout
reviewed existing rendering, persistence and controller risks in read-only task
`chalkline-markup-controls`; no concurrent source writes were delegated.

Related functions are grouped in domain/markup.py (lossless geometry and edits),
application/markup.py (defaults, selection and gesture transactions),
ui/MarkupPanel.qml (palette and editing controls) and ui/MarkupSurface.qml
(normalized pointer input and fullscreen pan). Studio delegates its existing
addShape entry point. Both draft and saved shapes use the shared painter.

Seven tools are exposed: arrow, line, circle, pen, rectangular zone, ground ring
and text. The panel includes six named colours, legacy text defaults/size range,
legacy global line thickness range and increments, a drawing selector, text
dialog, duplication/deletion, movement nudges, freeze/1/2/4-second/Stay-on presets
and source-time editing. Stay on preserves legacy visibility from the drawing's
source time; it does not rewrite the drawing time to the clip start.

Draw gestures stop review and frame-resume playback, preview transiently and
checkpoint on successful release. No-op/cancelled gestures create no undo entry.
Clip/document changes, intervening edits, seeking or export invalidate drafts.
Modal text results recheck the target before writing. Existing unsupported shapes
and fields remain saved; duplication retains their export rejection.

Scout correctly flagged project replacement on undo, review restarts from
touchCurrent, timing/keyframe preservation and export guards. Codex did not
adopt its suggestion to checkpoint on press: that would create undo entries for
cancelled strokes. Nor do we keep an index across mutations: selection references
are validated against the current live shape objects and invalidated after
replacement; gesture validity checks the project, selection generation and full
clip snapshot. Colour keys are retained, but the renderer also permits legacy hex
values; preserving those does not require normalizing them to a named swatch.

Evidence: 92 native tests and QML startup pass, including 10 new markup tests.
The 4K test paints every tool and checks nontransparent pixels. Actual QML mouse
and keyboard events verify pen gestures, Escape and fullscreen panning; real
button handlers verify palette actions and duplicate/delete. The encoded media
proof at E:/Chalkline/test-results/20260909-131548 includes all seven tools;
all frames decoded at 3840x2160/30 fps. Layout captures are ignored test artifacts.

On-canvas selection, grips, arbitrary zone corners, specialist tools, clipboard
copy/paste, tracking, inline text and general redo are still on the parity list.
No feature removals were proposed. The installed executable and live PWA were
not modified. The native source preview uses a separate project copy.
