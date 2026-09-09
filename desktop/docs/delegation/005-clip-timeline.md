# Task 005 — clip timeline and function grouping

User requested another bounded packet and related functions grouped together.
Codex implemented the native source changes; Atlas Scout reviewed the inherited
trim/timing behavior in read-only task `chalkline-clip-timeline`. No live PWA,
installed executable, saved user project or export was changed.

## Delivered

- Source-time trim handles and half-second nudges, with a fixed drag viewport.
- Freeze, slow-motion and drawing lanes; click seeks without reselecting the
  clip. Double-click opens existing freeze/slow timing editors.
- Drag previews remain transient until release. One undo restores the complete
  pre-drag clip. Escape, switching clip/document, another edit or export cancels
  stale interaction state. Numeric trim rejects empty clips and ignores no-ops.
- Annotations and unknown fields remain saved at their original absolute times.
  Markers outside the new trim range are dimmed within the visible viewport.
- Playback lives below the video with extra navigation in More. Clip details,
  coaching notes, freeze/slow timing, drawing tools and export have labeled
  inspector groups. Project actions and Undo live together in the top bar.

## Source locations

| Responsibility | Location under desktop/src/chalkline |
| --- | --- |
| Trim math and lane data, independent of Qt | domain/clip_timeline.py |
| Pending drag, validity, commit, cancel, nudge | application/clip_timeline.py |
| Strip display and pointer interaction | ui/ClipTimeline.qml |
| Transport and navigation | ui/PlaybackPanel.qml |
| Grouped clip editing sections | ui/ClipInspector.qml |
| Shared dense action sizing | ui/ActionButton.qml |
| Notes editor and numerical timing editors | ui/NotesPanel.qml, ui/TimingPanel.qml |
| Window orchestration, video and global shortcuts | ui/Main.qml |

Notes draft methods in Studio now sit alongside its other notes methods.
Shared native-window setup is in tests/qml_fixture.py; notes and timeline
regressions use it rather than duplicating engine/font/window lifetime code.
Studio still has other responsibilities to extract in future feature packets;
this is not a completed whole-application restructuring.

## Scout review and lead verification

Scout identified source offset versus tag-relative pre/post timing, unchecked
numeric trim, stale mutable selection during drag, preserving out-of-trim
annotations, legacy single slow-zone dictionaries, and seek/reselection hazards.
Codex checked these against the PWA and native source and covered the resulting
behavior in tests. PWA startTrimDrag rounds pre/post to half-seconds; this packet
uses that interval for trim instead of the finer snapping used by timing edits.
The original annotations are never shifted to compensate for a trim.
Raw response and session metadata remain in ignored agents/results and ledger.

## Evidence and limits

82 native tests and QML startup pass, including 11 timeline/layout regressions.
Real QTest pointer/keyboard events exercise drag, release, Escape and seeking.
The minimum 1050x720 window retains the panels within its width; opening More
preserves video height. Basic style matches the production launcher. Layout
captures at 1050x720 and 1440x920 were inspected; the offscreen video surface
does not prove decoded playback and is black in those captures.

Freeze/slow beat dragging, duration grips, general markup editing and the
whole-match rail are still pending. No feature removal is proposed. Export
algorithms were untouched; the previous decoded true-4K proof remains the media
milestone. This packet has not been packaged, committed, pushed or deployed.
