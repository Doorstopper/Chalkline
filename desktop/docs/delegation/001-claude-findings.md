I read the scope docs and every file listed; no files were modified and nothing was run.

## Findings (highest impact first)

### 1. Notes text is bound to the panel, not to the clip — switching clips loses or misapplies notes
**Where:** `desktop/src/chalkline/ui/NotesPanel.qml:11` and `:14`, interacting with `desktop/src/chalkline/ui/Main.qml:128`.

**Trigger:** Select clip A, click into the notes box, type text, then click clip B in the strip without clicking anywhere else first.

**Failure:** The clip strip delegate is a plain `MouseArea` (`Main.qml:128`), which does not take active focus, so `onActiveFocusChanged` (`NotesPanel.qml:14`) never fires and the typed text is never committed to clip A. Meanwhile `selectClipId` emits `changed`, so `studio.current` now refers to clip B. Both possible outcomes are defects:
- If the `text: studio.current.notes || ""` binding (`:11`) is still live, the field is overwritten with clip B's notes and clip A's typing is gone with no undo entry (nothing was ever written to the model).
- If the binding was destroyed by the user's typing (standard `TextInput`/`TextEdit` behaviour), the field keeps clip A's text while clip B is selected; the next focus-out writes clip A's text into **clip B's** `notes`, and "Apply at freeze" (`:45`) burns clip A's text onto clip B's timeline.

This is distinct from the known "notes-field sync on pause/seek" omission — it is per-clip identity, not playhead sync.

**Status:** Confirmed structural defect from code. Which of the two branches occurs needs an interactive check; both lose or misdirect edits.

**Minimal fix:** Track the bound clip id in the panel and commit-then-rebind on change, rather than relying on focus:
```qml
property string boundId: ""
Connections { target: studio; function onChanged() {
    var id = studio.current.id || "";
    if (id === notes.boundId) return;
    if (notes.boundId) studio.setTextForClip(notes.boundId, "notes", notes.text);
    notes.boundId = id; notes.text = studio.current.notes || "";
}}
```
with a new `setTextForClip(id, key, value)` slot beside `setText` (`studio.py:743`) that resolves the mark by id. Test: unit-test that `setTextForClip` writes to the mark with the given id even when `selected` has already moved on.

### 2. "Load text at this freeze" both under-finds and silently clears notes
**Where:** `desktop/src/chalkline/domain/notes.py:21` (match window `< .15`) versus `:42-44` (apply snaps within `<= .5`); consumed at `desktop/src/chalkline/application/studio.py:216` and `desktop/src/chalkline/ui/NotesPanel.qml:47`.

**Trigger:** Clip with a freeze note at t=18.0. Pause/scrub to 18.35 and press "Load text at this freeze".

**Failure:** `noteTextAtPlayhead` uses the raw playhead with the 0.15 s window, returns `''`, and `NotesPanel.qml:47` passes that straight into `setText("notes", "")`, which wipes the clip's raw notes field (`studio.py:745-748`). The user sees an empty box, retypes, and presses Apply — which *does* snap (the note's own beat is a stop via `freeze_stops`, `timeline.py:40-41`), so it overwrites the existing note at 18.0. Net effect: the existing note text is replaced by text the user believed was new.

**Status:** Confirmed; both halves are pure Python logic.

**Minimal fix:** Factor the snap out of `apply_notes` into `note_beat(mark, position, offset, duration, hold)` and use it in both `apply_notes` (`notes.py:39-44`) and `noteTextAtPlayhead`; guard the QML button with `var t = studio.noteTextAtPlayhead(); if (t) notes.text = t;` so an empty result never clears stored notes. Test: freeze note applied at 18.0, `_source_time = 18.35`, assert `noteTextAtPlayhead()` returns the text and that a subsequent apply updates rather than creates.

### 3. `place_notes` measures with the *previous* anchor, so repositioning re-wraps text into a narrow column
**Where:** `desktop/src/chalkline/rendering/text_layout.py:43` calls `measure_text` before writing `shape['a']` at `:48`; `measure_text:23-26` derives the wrap width from `shape['a']['x']`.

**Trigger:** Apply a short whole-clip note with position = top right (anchor lands near `x≈.86`), then change the text size or press a different position button — `studio.setNotesStyle` calls `place_notes` on the existing shape (`studio.py:176`).

**Failure:** `cap = max(.15, .97-.86) = .15`, so the wrap limit collapses to 15 % of frame width and a one-line note becomes a tall narrow column. It also ratchets: the narrower box pushes `x` further right (`.96-box_width`), which narrows `cap` again on the next change. The existing test passes only because it always starts from `a.x = .04` (`test_notes.py:68`).

**Status:** Confirmed by code path; the numeric example above follows directly from `:24-26`.

**Minimal fix:** Give `measure_text` an explicit `left` parameter and have `place_notes` pass the placement bound (`0.04`) instead of the stale anchor, keeping the current behaviour for manually dragged text. Test: `place_notes` on a shape with `a.x = .86` and short text yields the same line count as the same shape at `a.x = .04`.

### 4. Colour / size / nine-position controls do not affect a per-freeze note
**Where:** `desktop/src/chalkline/application/studio.py:171` (`index = find_note(candidate)` with `at=None`) and `:197-198` (`place_notes` only when `created`).

**Trigger:** Apply a note at a freeze, leave the playhead on that freeze, then change the colour, size, or click a different position button.

**Failure:** `find_note(mark)` with `at=None` only matches a shape with `keep` set (`notes.py:19`), i.e. the whole-clip note. Per-freeze notes carry `linger: 0` and no `keep` (`notes.py:57-58`), so they are never found: the style change is stored in settings but the visible note is unchanged. Re-pressing "Apply at freeze" does not rescue the position either, because `place_notes` runs only on creation (`studio.py:197`) — so the nine-position grid can never move an existing freeze note.

**Status:** Confirmed.

**Minimal fix:** In `setNotesStyle`, look up the playhead note first and fall back to the whole-clip note (`index = find_note(candidate, beat)` then `find_note(candidate)`), reusing the shared `note_beat` helper from finding 2; and in `applyNotes`, call `place_notes` when the requested column/row differs from the stored style, not only when `created`. Test: apply a freeze note, call `setNotesStyle` with a new column, assert the shape's `color`/`fs`/`a` all changed.

### 5. A whole-clip note and a freeze note render on top of each other
**Where:** `desktop/src/chalkline/rendering/text_layout.py:46-47` (fixed anchors per column/row) with `desktop/src/chalkline/rendering/annotations.py:36-39` (`keep` notes stay visible through freezes).

**Trigger:** "Apply to whole clip", then "Apply at freeze" on the same clip with the default top-left position; play or export through that freeze.

**Failure:** For column 0 / row 0 both notes get exactly `a = {x: .04, y: .06}` (the expression is position-only, independent of text), and `alpha_at` returns 1 for both at the freeze, so two backing plates and two text blocks are drawn at identical coordinates — overlapping, unreadable text. `test_notes.py:40-52` constructs precisely this coexistence case but never renders it.

**Status:** Confirmed as a deterministic double-draw from code; the exact visual severity is worth a look at a rendered frame.

**Minimal fix:** When placing a note, offset it past any other note that is visible at the same beat and same column/row — e.g. in `applyNotes`, if a `keep` note exists, shift the new freeze note's `y` down by that note's measured box height. Test: apply whole-clip then freeze notes at the same position and assert the two shapes' `a['y']` differ by at least the whole-clip note's height.

## Suggested bounded implementation task
**Make the notes beat and the notes field authoritative (findings 1 and 2).** Add `note_beat(mark, position, offset, duration, hold)` to `notes.py`, use it in `apply_notes` and in `Studio.noteTextAtPlayhead`; add a `setTextForClip(id, key, value)` slot next to `setText`; rework the `NotesPanel` `TextArea` to commit to the previously bound clip id and rebind on clip change instead of relying on focus loss; guard the Load button against an empty result. Cover it with two Python tests (snapped lookup at ±0.35 s of a freeze note; `setTextForClip` writing by id after the selection has moved) and add the clip-switch case to the pending interactive checklist in `verification.md`.
