# Task 003: stable note placement when resizing

Fixed in source after an Atlas Scout investigation. Lead-confirmed reproduction
with the native Qt font metrics:

- Text `Keep space`, size 19, initial anchor (0.04, 0.06), width 900, height 506.
- place_notes(shape, 2, 0, 900, 506) puts the note at top right.
- Change size to 48, then call place_notes again: lines become `Keep`, `space`,
  and x becomes approximately 0.82778.
- Place the same size-48 text fresh from (0.04, 0.06): one line `Keep space`,
  x approximately 0.69667.

Cause: place_notes measures the new text using a wrap limit derived from the old
anchor. Desired explicit placement should depend on current text/size/position,
not its previous location. Ordinary painting of manually placed text should
retain its current right-edge wrapping rules.

Proposed exclusive scope: rendering/text_layout.py and focused notes rendering
tests. Preserve stored legacy fields and manually placed anchors on reapply.
Verify resizing in both directions, position changes, multiline notes and 4K
measurement. Do not introduce automatic collision avoidance or resized-box
export support as part of this task. Return a small patch for lead review.

## Lead implementation and evidence

`place_notes` now measures a shallow copy with the neutral anchor (.04, .06),
then writes only the requested final anchor to the original shape. Ordinary
`measure_text`/`paint_text` calls still use the stored manual anchor. Source call
sites are preset style changes and initial notes creation; this is not a manual
drag path. Reapply still preserves an existing manually positioned note.

Three rendering regressions cover 19-to-48-to-19 resize round trips, all nine
positions with stale anchors, multiline text, explicit width and unchanged manual
right-edge wrapping, at both 900x506 and 3840x2160. The two applicable new tests
failed before the fix, then passed afterward.

Correction to Scout's explanation: a centre anchor is `.5 - box_width/2`, so
its unclamped cap is `.47 + box_width/2`, not at least .8. For a measured box at
most 2/3 wide, this remains at least the measured width, so the chosen lines fit.
The tests verify the post-placement lines using the actual native font metrics.
This does not add oversized unbreakable-word handling or resized-box export support.
