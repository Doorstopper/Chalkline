# Native media milestone — 2026-09-08

Baseline remains PWA v212. This is a native proof of concept, not full parity.

## Subsequent source packets — automated checks passed, interactive checks pending

Timing-drag packet: **103 native tests and QML startup passed** before the E:
development folder became unavailable. Eleven new regressions cover raw-index
freeze movement without shifting drawings, offset/snap/clamp behavior, slow
non-crossing and 0.1-second minimum, legacy dictionaries, unknown fields/order,
impossible intervals, nearby manual points, real pointer ownership across preview
rebuilds, single undo and project round trips, no-op clicks, automatic beat hints,
Escape/selection changes, other-edit/document/export invalidation, and actual
double-click dialog dispatch. Opus supplied the pure domain helper proposal;
Codex integrated it and reviewed the implementation. Fable's review stopped at
the configured estimated per-run budget before delivering findings; it is not
accepted as a completed review.

`verify_media.py --markup --timing-drag` now defines an additional proof with
the manual freeze moved to 3.5 s and slow end shortened to 3.4 s. Its expected
duration is independently calculated as 5.4 s. **This new media proof has not
run**: its launch failed because E:/Chalkline/development-runtime/Scripts/python.exe
and E:/Chalkline were no longer available. The user was asked whether the drive
was disconnected or the folder moved. No further preview was launched and no
package was made. Restore access, run this proof, inspect the new handles, and
record the Opus acceptance in Atlas before considering the packet fully verified.

Markup controls packet: **92 native tests and QML startup pass**. Ten new
regressions cover tool geometry, timing/unknown-field preservation, clamped
movement including ground keyframes, actual QML pen strokes, transient preview,
single undo, Escape/clip switching, seek/document/edit/export cancellation,
text-dialog cancellation and late results, selected edits/duplicate/delete and
project round trips, every tool's 4K painter pixels, thickness undo, and fullscreen
pan through the extracted input surface. Layout was inspected at 1440x920 and
1050x720. The palette is first in the scrollable inspector.

`tests/verify_media.py --markup` exported all seven tools from the original
3840x2160 test footage to `E:\Chalkline\test-results\20260909-131548\`.
Output is H.264, 3840x2160, 30 fps, 5.033008 seconds. All frames decoded;
source/freeze/motion samples were non-black. Silent source, fractional FPS and
export rejection/cancellation checks also passed. The sample project retains
global line thickness for preview/export consistency. A separate editable
preview copy is `E:\Chalkline\projects\Markup-work-in-progress-20260909-131901.chalkline`.
The old installed binary remains unchanged; source launch is through
`scripts/run.ps1 -Project <path>`. General on-canvas editing remains pending.
The visible Windows preview was launched with the default Qt graphics backend,
without the offscreen tests' software-backend override. Its native window,
LoadedMedia state and valid video frame were confirmed. The captured live window
was visually inspected: actual soccer footage, all seven sample markups and the
new palette are visible. It was left open for the user, paused at source 3 s.

Clip timeline and grouping packet: **82 native tests and QML startup pass**.
Eleven new tests cover source offset and bounds, half-second trim snapping,
unknown-field/annotation preservation, dimmed inactive markers, real mouse drag,
fixed viewport during drag, one-step undo, Escape, selection/project replacement,
concurrent edits/export invalidation, seek without reselection, invalid numeric
trim, and minimum-window layout. The shared QML fixture now uses the production
Basic control style. Layout captures at 1440x920 and 1050x720 were inspected;
the initial small-window clipping was corrected with shared action sizing.
The More popup keeps extra playback controls together without shrinking the
video. Captures in ignored `desktop/test-results/timeline/` validate UI layout
only: the offscreen video surface is black, so these are not playback evidence.
No export algorithms changed or new encoded-media proof was run this packet.
Freeze/slow beat dragging remains pending. See delegation task 005 for the
module map and reviewed Scout findings. Installed binaries remain unchanged.

Freeze-note synchronization packet: **71 native tests and QML startup pass**.
Automatic seek/pause/freeze-entry loading
now preserves active typing and saved drafts; blank freezes clear only the editor.
Explicit Load uses the same half-second nearby-freeze selection as Apply. Loaded
colours remain ephemeral until applied. Two domain and seven QML regressions cover
this behavior, including ordinary playback updates, project undo and same-clip
reselection. No rendering or export algorithms changed in this packet.

Previous notes reliability packet: **62 native tests and QML startup passed**.
Eight new real-QML tests cover typed draft/cursor preservation through general
refreshes, switching clips without losing or cross-writing drafts, actual Ctrl+S
while focused, direct save and cancelled close, grouped project undo, editor undo,
paste/IME commits, Apply and explicit load. Draft changes now persist immediately
without rebuilding playback. Three rendering regressions cover deterministic
preset placement after resizing/repositioning at 900px and 4K, explicit widths,
multiline notes, and unchanged wrapping for manually positioned text.

Atlas's supporting CLI has 19 passing offline tests after a Windows Unicode
console-output fix. Scout's placement suggestion was checked and its incorrect
centre-column arithmetic corrected before integration. See the delegation records.
These are source changes; the installed executable has not been replaced.

The refreshed media integration check also passed, writing only to
`E:\Chalkline\test-results\20260908-223518\`. The H.264 proof is 3840x2160,
30 fps and 5.033008 seconds. Every frame decoded, sampled source/freeze/motion
frames were non-black, and silent-source/fractional-FPS/rejection/cancellation
checks passed. The proof now includes a top-right note placed at size 19 and
resized/re-placed at 48. The extracted freeze frame was visually checked using
`freeze-preview.png`: "Keep space" stays on one line and is readable, along with
the arrow and caption. Original 4K frames and `verification.json` are retained.

The installed `E:\Chalkline\Native\Chalkline.exe` is still the earlier media
prototype. These subsequent source changes have NOT been packaged or accepted:

- Tag pads: seven legacy defaults, native editor, one-off custom tag, first ten
  Q–P shortcuts, reaction lag only while playing, default player and auto-edit loop.
- Clip management: ID-based selection through sorting/filtering, chronological
  numbering, group labels, player scope, kind/export indicators, category/player/
  prompt/notes editing, caption count, delete/clear and sync tombstones.
- Project reliability: prepare/probe before replacing the current session, keep
  edits/history on failed or cancelled opens, Save As, clear stale relative paths
  when relocating footage, and reject malformed clip IDs/times on load/save.
- Transport: skip ±1/5/10/20 seconds; all seven legacy speeds; mute indicator;
  start/loop/close; chronological previous/next clip within the player filter;
  cycling markup points; play on after this/latest clip; Spot/Resume bookmarks;
  keyboard shortcuts for clip navigation and speed; frame-button delayed resume.
  Pausing edited playback retains elapsed freeze hold, and seeking retains the
  chosen match playback rate. Explicit slow zones override that rate.
- Freeze/slow editing: native per-point dialogs, numerical time and duration
  edits, deletion with undo, slow in/out/cancel using the selected slow speed,
  global auto-freeze/hold and whole-clip drawing display. Unknown timing fields
  survive edits. Source times snap to tenths; freeze holds snap to half seconds.
  Freeze merging now occurs before clip-boundary filtering, matching v212.
- Notes: separate text marks at each freeze and across the whole clip, nearby
  freeze snapping, matching-box updates preserving manually placed anchors and
  unknown fields, colour/size/nine-position controls, explicit load-at-playhead.
  The shared text painter now wraps paragraphs and draws a dark backing plate
  using the same metrics as note placement. Existing resized-text export guards
  remain; font metrics use Segoe UI and still need visual comparison to the PWA.

The earlier quota-related approval rejection cleared on the next normally
approved validation attempt. All 26 earlier tests and QML startup then passed.
After the notes packet, `scripts/validate.ps1` passed all **51 tests** and
QML startup. A second offscreen startup loaded the existing Native proof project
and its real source media, exercising populated freeze/slow lists without QML
errors. Ten timing tests cover offset independence, snapping/clamping, rejected
edits, legacy single zones, unknown fields, deletion/undo, settings, in/out/cancel,
overlap precedence and freeze-boundary merging. The transport tests use a fake
player and clock; they verify controller state, not decoder/frame/audio timing.
Six additional notes tests cover per-freeze/whole-clip coexistence, repeat apply,
manual-anchor/unknown-field preservation, undo and round trips, text wrapping,
nine-position placement, and 3840x2160 rendering with correct freeze visibility.
A 4K painter proof was generated in ignored `desktop/test-results/notes/`; its
960px preview was visually inspected for readable text, wrapping, dark backing
and bottom-right positioning. This is a painter proof, not a new encoded-video
export or interactive UI acceptance test.

Next verification: interactively check tag hotkeys versus text entry, auto-edit looping, sorting/
filtering and selection, pad dialog save/cancel, deletion/undo, project switching
with invalid/missing media and Save As, and the new transport and timing controls
during real playback. Notes still require general text drag/inline editing;
automatic pause/seek synchronization and explicit nearby-freeze loading now have
domain and QML coverage. Freeze hold popovers and markup duration dragging remain
pending; source trim, manual freeze and slow edge handles now have QML
coverage. Build a fresh portable package only after these pass. This does not yet
handle a codec failure reported asynchronously by
QMediaPlayer after FFprobe succeeds; missing-media identity checks also remain.

The sections below record the previously verified, packaged media milestone.

## Verified

- Ten core tests pass: legacy unknown-field preservation and offset semantics,
  project save/open, relative media after moving a project folder, rejecting future
  schema versions, freeze merging/manual freezes, source clamping and slow timing.
- QML startup passes with Qt 6.11.2 / Python 3.12.10.
- The existing 60-second XootGo H.264 test copy was used as input (3840x2160, 30 fps).
- A five-second annotated clip with a one-second freeze and half-speed section
  exported at 3840x2160, H.264, 30 fps; measured container duration 5.033008 s.
- Every output frame decoded without FFmpeg errors. Sampled source/freeze/motion
  frames were non-black. The exported freeze image was visually inspected; arrow
  and caption are present and readable. An offscreen font issue was fixed before
  accepting the result.
- Synthetic no-audio input receives an audio stream, and 30000/1001 fps survives.
- Export rejects unsupported drawing tools, existing output names and non-4K
  sources in true-4K mode. Pre-start cancellation passes.
- Interactive native source playback, pause, fullscreen, zoom to 120%, drag pan
  and return to the editing layout were observed on the ZBook.

Proof artifacts: `E:\Chalkline\test-results\20260908-144449\`.
`verification.json` records export metadata; `native-proof-4K.mp4` is the output,
and `Native proof.chalkline` is the project used to exercise the UI.

## Packaging

One-folder PyInstaller build with bundled FFmpeg/FFprobe. A custom QtQml hook
excludes unrelated QML families because the default hook pulled unused QtWebEngine
binaries into the first package despite Python-module exclusions. Package startup
and browser-binary absence are checked by `scripts/check-package.ps1`.
The corrected package passed both checks and was placed at
`E:\Chalkline\Native\Chalkline.exe`, with the proof project in its `projects/`
folder. Python and Qt are bundled; FFmpeg and FFprobe are in `tools/`.

## Not yet verified / not yet complete

- Long original camera recordings, variable-frame-rate files, HDR/colour-range
  parity and representative clips containing every legacy drawing tool.
- Frame-exact preview seeking and audio synchronisation at edit transitions.
- Active mid-encode cancellation via UI, UI export workflow and long-job recovery.
- Full voiceover/music mixing, sync interoperability, all editing tools and the
  rest of the feature matrix in `parity.md`.
- Release signing, update installation/rollback, file association and third-party
  redistribution notices/source-offer requirements for a public release.

Nothing was committed, pushed or deployed during this milestone. No live PWA files
were changed. Development dependencies and generated artifacts were placed on E:.
