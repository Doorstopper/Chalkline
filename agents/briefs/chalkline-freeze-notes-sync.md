# Task: chalkline-freeze-notes-sync
## Objective
Review the edge cases for restoring the legacy freeze-notes field synchronization in the native app.
## Scope
Read index.html only lines 2040-2145, desktop/src/chalkline/domain/notes.py, desktop/src/chalkline/ui/NotesPanel.qml, and Studio.noteTextAtPlayhead / notesStyle / setNotesStyle / applyNotes in desktop/src/chalkline/application/studio.py. Atlas is editing these files; use the design below as the review target rather than assuming a stable implementation.
## What to produce
At most 250 words of specific risks or missed parity cases. Design: automatic loading only when the playhead is resting within .15s of an actual freeze and the notes editor is not focused; outside freezes leave its displayed text alone. A freeze with no text clears only the displayed field, not saved draft data. Programmatic loading must not create undo entries or change applied shapes. User edits persist immediately with existing draft grouping. Explicit Load snaps to the nearest freeze within .5s like Apply and leaves drafts alone if none exists. Loading a note's colour is an ephemeral editor choice, not a style mutation of the whole-clip annotation.
## Evidence required
Cite source paths and line ranges. Identify any factual uncertainty. Do not claim to have tested anything.
## Out of scope
No edits, commands, other files, delegation, timeline redesign, or new drawing features. Do not re-inventory the PWA.
