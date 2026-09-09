# Claude Code task 002: preserve notes drafts through UI refreshes

Lead: Codex. Work on this one confirmed defect only. Return a proposed unified
diff in your response; do not write files, run commands, spawn agents or deploy.
Use Read/Glob/Grep only. Codex will inspect/apply the patch and run validation.

Confirmed by Codex with a real offscreen QML input probe:

1. Open a selected clip with notes `Original`.
2. Focus the NotesPanel TextArea and type `x` using QTest.keyClick.
3. The field reads `Originalx`, but the stored mark still reads `Original`.
4. Call studio.mute(), which emits the general changed signal without changing
   focus. The text binding reevaluates and the field reverts to `Original`.

Reproduction script: desktop/scratch/delegation/probe_notes_draft.py.
Root cause candidate: NotesPanel binds text to studio.current.notes, but stores
edits only when focus is lost. A regular changed signal can overwrite the draft.

Implement the smallest reliable fix. Preserve ongoing typing/cursor behaviour,
keep Save/Ctrl+S from omitting a focused draft, and avoid writing an old clip's
draft into a newly selected clip. Keep load-at-playhead and Apply working.
Do not implement automatic freeze-field sync or redesign undo in this task.

Allowed proposed changes:
- desktop/src/chalkline/ui/NotesPanel.qml
- one new desktop/tests/test_notes_ui.py
Only propose Studio changes if demonstrably necessary; explain why first.

Regression tests must exercise actual QML key input, not just setText(). Cover
draft survival after unrelated changed signals, clip switching, and saving while
focused (mock only the picker if needed, use a temporary .chalkline destination).
Use the project's existing offscreen Qt test approach, QApplication singleton,
and ensure_fonts(). Avoid requiring real media or timers/sleeps. Destroy the
QML engine before its Studio context. Do not claim tests were run.

Deliver the patch and a concise explanation. No additional feature work.
