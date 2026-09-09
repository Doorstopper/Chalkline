# Desktop parity contract

Baseline: PWA v212, confirmed in index.html on 2026-09-08. The full inherited
Claude UI/data and video/export inventories are in `legacy-inventory.json`.
Those inventories, including per-feature controls and notes, are the acceptance
checklist; the grouped table below is a progress summary, not a reduced scope.

User requirement: 100% of existing user functionality carries over, except the
unnecessary .bat conversion workflow. A prototype is not an accepted replacement.
No other user capability may be removed without an explicit decision.

| Feature group | Prototype status | Remaining acceptance work |
| --- | --- | --- |
| Match loading | Partial: native picker and source metadata; staged switching failure paths tested | Drop/reopen, per-match library, loading race/retry, safe switch variants, codec diagnostics |
| Tag pads | Source implemented: seven defaults, editable/custom pads, Q–P, reaction lag, auto-edit looping, default player | Interactive QML checks and looping acceptance; packaging |
| Clip strip | Source implemented: ID selection, chronological numbers, sort/group labels/player filter, kind/export flags, delete/clear/tombstones | Thumbnails, interactive acceptance, numbering parity across all edits; packaging |
| Clip editing | Source implemented: label, caption/counter, validated pre/post, category, kind, multiple players, prompt and raw notes; grouped inspector panels | Broader interactive acceptance; packaging |
| Transport | Source implemented and state-tested: pause/resume edited review, seek, frame step/button resume, all seven speeds, mute, ±1/5/10/20s skip, loop/restart/close, clip/markup navigation, both play-on modes | Decoder/frame precision, interactive controls and audio transition acceptance; packaging |
| Whole-match rail | Pending | Clip ticks, hover cards, keyboard selection, trim handles, bookmark |
| Clip trim strip | Partial: source trim handles/nudges, manual freeze dragging, slow start/end grips, fixed drag scale, separate lanes, click-to-seek and timing dialogs; cancellation and one-step undo tested | General markup timing dragging/duration grips, broader decoder acceptance; packaging |
| Freezes | Source implemented: add/edit/delete numerical timing, manual timeline dragging, custom 0.5–30s holds, shared plan, global auto-freeze/hold and whole-clip drawing display | Timeline hold popover, hold preset buttons, text/markup shortcuts, freeze-with-no-clip, broader interactive edge acceptance; packaging |
| Notes | Source implemented: colour/size/nine-position controls, apply at freeze/whole clip, update matching note without duplicates, wrapped text with backing plate. Automatic freeze text/colour loading preserves focused typing and saved drafts; explicit Load snaps to nearby freezes. Drafts survive refresh/clip changes and focused Save; preset resizing is stable. Real-QML and 4K layout regressions pass | Drag/inline editing through general text tools; broader interactive and decoder-timing acceptance; packaging |
| Telestration | Partial: create arrow/line/circle/pen/rectangular zone/ground ring/text with transient strokes; grouped palette, named colours, global thickness, text size/edit dialog, list selection, duplicate/delete, movement nudges, source time and display presets; one-step undo and 4K rendering tested | Remaining tools out of 18, on-canvas selection/marquee/grips, resize, clipboard copy/paste, inline text, line labels, flip/bow, plane/taper, arbitrary zone corners, custom linger input, tracking and full undo/redo parity |
| Zoom/pan | Partial: wheel/buttons/reset and drag | Cursor-centred zoom, transform parity, loupe and interaction regression tests |
| Fullscreen | Partial: native fullscreen and pan | Auto-hide controls/cursor, full keyboard parity, exit state restoration |
| Spot / Resume | Source implemented: absolute bookmark persisted in project, toggle near same spot, resume match playback | Interactive acceptance and clickable star on whole-match rail; packaging |
| Slow sections | Source implemented: in/out/cancel, add/edit/delete numerical timing, non-crossing timeline edge grips, all three rates, legacy single-zone edits; dragging preserves existing overlap precedence/order | Broader interactive boundary/rate acceptance; packaging |
| Persistence | Partial: versioned .chalkline, legacy field preservation, Save As, document validation; failure-path tests pass | Autosave/recovery, recent library, preferences, backup/restore, migrations and missing-media identity checks |
| Sync / handoff | Pending; retained, optional and off by default | Compatible codes, merge/tombstones, copy/share, configured endpoint push/pull and optional auto-sync |
| Help / version / errors | Partial: prototype version/status/errors | Native help, shortcuts, accessible dialogs/toasts, user-facing diagnostics |
| Still exports | Pending | Source-resolution PNG and current-view snapshot (native replacements for both existing buttons) |
| Clip exports | Partial: annotated 4K H.264 proof | Resolution/FPS choices, clean/original-speed cuts, all markup timing, output folder preferences |
| Batch / reels | Pending | All/player/category/kind scopes, ordered clips, title cards/duration, individual files plus reel |
| Audio | Partial: original audio, tempo correction, silent freeze/no-audio handling | Original mute UI, microphone voiceover/count-in, music selection/volume, mix with rendered timeline |
| Cut lists / interchange | Pending; retained | JSON save/load, per-player cut-list text and reusable export presets |
| Compact/touch layout | Pending | Small-window/touch adaptation. Native Windows build does not replace the phone PWA |
| Distribution / updates | Partial: portable executable and repeatable isolated builds | File association, installed updates/rollback, release automation |

## Explicit replacement of mechanisms

- .bat generation/extraction/manual execution is replaced by in-app FFmpeg jobs.
- Browser MediaRecorder/VideoFrame/screen-capture export mechanisms are replaced
  by native equivalents; still/clip/reel/clean-cut outcomes are retained.
- Service worker, browser filesystem handles and localStorage/IndexedDB become
  native runtime, project/settings files and source references.
- Browser-only readback diagnostics become native playback/export diagnostics.
- Browser-readable H.264 conversion workaround is unnecessary; clean export and
  lower-resolution output choices remain. Optional playback proxies are a future
  implementation detail and never an export source.
- Dead/unreachable legacy code is not a user capability.

## Decisions still belonging to the user

No extra feature removals have been approved. In particular, do not remove Sync,
handoff codes, cut-list text or snapshot functionality because an inventory calls
them old or broken. Cloud sync remains opt-in; offline work needs no service.

## Prototype limitations

The prototype creates seven simple annotation types, using shared preview/export
rendering; unsupported geometry options and tools block export. Preserving
data is not equivalent to implementing its behaviour. Imported projects must not
be treated as visually complete previews yet.

Clip review currently uses a wall-clock timeline and Qt seeking; exact frame and
audio synchronisation at segment transitions still requires validation/improvement.
No promise of frame-accurate scrubbing is made from QMediaPlayer alone.

The current export streams an RGBA annotation layer to FFmpeg, keeping memory and
disk bounded. This supports time-varying annotations but needs performance profiling
before long reels. The proof has a ten-minute clip limit; this is a prototype guard,
not a proposed final product limit.

Full parity acceptance requires representative projects covering every tool/control,
preview/export comparison, migrated data round trips, audio and sync checks,
fullscreen pan regressions, and packaged operation with networking unavailable.
