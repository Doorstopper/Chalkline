# Task: chalkline-notes-placement
## Objective
Identify the smallest reliable fix for note wrapping that depends on an old anchor during preset placement.
## Scope
Only desktop/src/chalkline/rendering/text_layout.py, desktop/tests/test_notes.py, and desktop/docs/delegation/003-notes-placement.md. Atlas is independently fixing NotesPanel.qml; do not inspect or propose changes there.
## What to produce
At most 350 words: explain the defect, propose the exact small change, and list two meaningful regression cases. Confirmed reproduction: place 'Keep space' at size 19 top-right on 900x506, increase fs to 48 and place again; it wraps while fresh placement at fs 48 stays on one line. Check whether explicit width and non-preset/manual positioning would be affected. Do not broaden scope.
## Evidence required
Cite paths and line ranges. Distinguish source reasoning from tests; Atlas will run the tests.
## Out of scope
No file edits, commands, delegation, deployment, or unrelated reading. Do not change manually positioned text behavior or propose cosmetic redesigns.
