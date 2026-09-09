# Claude Code task 001: notes packet review

Lead: Codex. Assignee: local Claude Code. User has explicitly requested this
collaboration. Review only; do not modify files, run commands, spawn agents,
contact other services, install anything, commit, push, or deploy.

Repository: C:\Users\ChadFerguson\Documents\Chalkline-repo.
Read CLAUDE.md for PWA context, but this task concerns only the separate native
desktop implementation. Read desktop/docs/parity.md and the subsequent-packets
section of desktop/docs/verification.md for scope. The live PWA is untouched.
Do not re-inventory index.html or read account/configuration/credential files.

Task: independently review the latest notes implementation for concrete bugs
that would lose edits, apply notes to the wrong clip/freeze, render incorrectly,
or break native QML interaction. Inspect only the relevant source and tests:

- desktop/src/chalkline/domain/notes.py
- desktop/src/chalkline/rendering/text_layout.py
- desktop/src/chalkline/rendering/annotations.py
- desktop/src/chalkline/application/studio.py
- desktop/src/chalkline/ui/NotesPanel.qml
- desktop/src/chalkline/ui/Main.qml
- desktop/tests/test_notes.py

Baseline: all 51 tests and QML startup pass. A 4K notes painter sample was visually
checked. Interactive acceptance and packaging are still pending. Known remaining
scope: automatic notes-field sync on pause/seek, general text dragging/inline
editing, and resized-text export support. Do not report those known omissions as
new defects. The palette/font intentionally differs from the PWA.

Return at most five actionable findings, highest impact first. Each must include
an exact source file and line, a reproducible trigger, the actual failure, and a
specific minimal fix/test recommendation. Distinguish confirmed code defects from
hypotheses needing interactive checking. If no clear defects, say so. Finish with
one suggested bounded implementation task. Do not claim to have run tests.
