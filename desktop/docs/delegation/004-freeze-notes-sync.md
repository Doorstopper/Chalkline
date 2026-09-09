# Task 004: freeze-note field synchronization

Atlas scoped one read-only Scout design review, then implemented and verified
the change. Atlas task: `chalkline-freeze-notes-sync`; raw response, session and
estimated cost are in the ignored coordinator ledger/results. No worker edited files.

## Decisions checked against v212

The legacy implementation at index.html:2132-2143 loads freeze text on pause or
seek, skips the focused notes field, clears the displayed field for a blank freeze,
leaves it alone away from freezes, and loads the note colour. That navigation does
not itself write the stored clip draft. The native implementation preserves this
separation, including after unrelated changed notifications.

The explicit Load button additionally resolves the nearest freeze within .5s,
matching Apply's nearby-freeze selection. Automatic loading retains the strict
.15s resting-beat window. No nearby freeze is distinct from a real freeze with
no notes. Explicit Load leaves text alone and reports when no freeze is nearby.
Whole-clip notes are not substituted for missing per-freeze notes.

Loaded colour is an editor property and is passed to Apply; navigation never calls
the style setter, recolours whole-clip shapes, dirties the project, or adds undo
entries. User typing continues to save the draft immediately. Selection, document
replacement and undo reset the displayed draft context, including reselecting the
same clip.

Scout correctly identified the old generic-change mirror, unguarded programmatic
loads, ambiguous empty string, colour setter side effects, and trigger surface.
Atlas checked those findings against the source before integration. The review's
wording about the playing gate is clarified here: `studio.playing` stays true
during an automatic review hold. The implementation uses explicit seek, pause
and freeze-entry signals; it does not poll position or require `playing == false`.

## Validation

Two new domain tests cover tolerances, absolute times/offsets, merged stops,
blank freezes, zero holds, clip edges and ground-keyframe exclusion. Seven new
QML tests cover saved draft/shape preservation, active typing, blank versus absent
freeze, colour-aware Apply to the snapped beat, pause/automatic-hold triggers,
undo and reselecting the same clip. Existing real keyboard/paste/IME/Save tests
continue to pass.

No rendering/export algorithm or project schema changed. The previous encoded
4K proof remains the media evidence; this packet tests editor state and triggers.
The already-open preview is left running and does not hot-reload Python/QML code.
