# Delegated work

Codex is the lead: owns scope, priorities, task boundaries, integration and final
validation. Claude Code receives bounded assignments and returns findings or
changes for review. Passing a task to Claude is not acceptance of its output.

All existing Chalkline functionality remains required except the replaced .bat
conversion mechanism. Live PWA files are excluded. No delegated deployment,
dependency installation, release, or push is authorized by this task board.

| Task | Owner | Scope | State |
| --- | --- | --- | --- |
| 001 | Claude Code | Review notes data, rendering and QML interactions | Complete; findings triaged by lead |
| 002 | Codex, after rejected Claude proposal | Preserve drafts and verify real QML input | Fixed in source; 8 real-QML regressions pass |
| 003 | Atlas Scout investigation; Codex implementation | Stable note placement when resizing | Corrected by lead and fixed in source; 900px/4K regressions pass |
| 004 | Atlas Scout design review; Codex implementation | Load the correct notes at freeze points without draft loss | Implemented in source; domain and QML regressions pass |
| 005 | Atlas Scout review; Codex implementation | Clip trim timeline and related function grouping | Source implemented; 82 tests and QML startup pass; see 005-clip-timeline.md |
| 006 | Atlas Scout risk review; Codex implementation | Markup palette, creation and selected-shape controls; viewable native preview | Source implemented; 92 tests, QML startup and seven-tool true-4K proof pass |
| 007 | Opus/Bolt proposal; Codex integration; Fable/Lens review attempted | Manual freeze and slow edge timeline dragging | 103 tests and QML startup passed; Lens budget exhausted; fresh media/preview checks blocked by unavailable E:/Chalkline |

Claude Code CLI was found in the VS Code extension and reports an authenticated
Claude subscription. A dedicated sandboxed review process returned no output and
was stopped. A network-enabled retry was rejected by automatic approval review:
general permission to collaborate with Claude Code was not accepted as specific
permission to send private repository source/task contents to the Claude service.
The user then explicitly approved sending the source and task instructions.
The normally approved retry connected successfully. Review session:
`7fb8c780-f7c4-4361-8cca-8d9ec06efa3f`. Transcript:
`desktop/scratch/delegation/001-approved-stream.jsonl`. Its findings are saved in
`001-claude-findings.md`; they are reviewer claims, not blanket acceptance.

## Task 001 lead decisions

- Draft loss: **confirmed** with actual QML key input. `Originalx` reverted to
  `Original` on `studio.mute()` while still focused. Prioritize task 002. Require
  real QML tests for refreshes, clip switching, and save while focused, rather
  than accepting Python-only tests of an added setter.
- Load-at-playhead tolerance: queue for review. Apply snaps within 0.5 s whereas
  explicit lookup uses 0.15 s; distinguish missing text from deliberate clearing.
- Placement based on the old anchor: **confirmed** with native font metrics.
  Place `Keep space` top-right at size 19, then resize to 48: it wraps into two
  lines, while placing the same text fresh at size 48 stays on one line. Queue a
  separate renderer fix; do not expand task 002 into it.
- Freeze-note style controls: current whole-clip-only live changes follow the
  inherited PWA code. Treat direct styling at a freeze as an acceptance/design
  question, not automatically a newly introduced bug.
- Overlapping whole-clip and freeze notes: also possible in the PWA. Do not
  automatically move user-authored annotations as part of a bug fix. Keep general
  text positioning/editing on the parity backlog.

Task 002 requests a response-only patch limited to NotesPanel.qml and a new QML
test file. Claude has no write or command tools; Codex reviews/applies the patch
and runs tests. This protects the shared, currently uncommitted source tree.

Task 002 result is in `002-claude-proposal.md`. Lead rejected it: clip switching
still discards the draft, and its regression explicitly expects the old value
to remain instead of preserving typed text. Its Ctrl+S test also calls save()
after sending the shortcut, masking whether the shortcut itself saved. No
proposed source/test changes were applied. Follow-up is queued while the user
requested building the Atlas coordinator from the supplied brief.

## Lead acceptance gate

1. Read Claude's result and verify each claimed defect against the actual source.
2. Prioritize confirmed data-loss and preview/export correctness defects before
   adding more UI. Do not expand an assignment into a general rewrite.
3. Give implementation tasks exclusive file ownership, or an isolated scratch
   copy if another session may be editing those files.
4. Review the diff, run the relevant regression tests and QML startup, then run
   an interactive check where automation cannot establish the behaviour.
5. Update the parity tracker with evidence and limitations. A source-only pass
   is not a packaged-release acceptance. Keep the installed proof executable
   unchanged until a new package has passed its own checks.

Task 004 resolves the remaining load-at-playhead issue and automatic field sync.
Task 007 adds manual freeze and slow edge dragging. Its fresh media/preview
checks need the E:/Chalkline folder restored. Markup timing/duration handles and
general drawing/text editing remain on the parity backlog.
Keep each assignment bounded; do not launch an unattended chain of tasks.

## Resumed packet: notes fixes

Codex replaced the draft-loss implementation rather than applying task 002's
rejected patch. Notes now persist as typed, with guarded QML synchronization and
one project-undo snapshot per editing session. Save, selection, focus loss and
other project edits end the group. Draft edits do not rebuild the playback
timeline. Eight tests drive the actual QML field, including Ctrl+S without a
second save call, clip switching, paste/IME, text undo and project undo.

Scout investigated placement through Atlas task `chalkline-notes-placement` in
a fresh session. Its diagnosis and one-line proposal were independently checked
and implemented. Its report's centre-column cap claim (at least .8) is incorrect;
the actual unclamped cap is `.47 + box_width/2`. The report as written is rejected,
but the corrected implementation passes the regressions. Details are in task 003.
Raw response/session/cost remain in ignored `agents/results/` and the Atlas ledger.

One local Atlas defect surfaced while printing Scout's Unicode output in a
legacy Windows console encoding. The result and cost had already been persisted;
no Claude rerun was needed. Atlas now emits UTF-8 and has a regression test.

Machine transcripts belong in ignored `desktop/scratch/delegation/`; accepted
findings and decisions belong here. Use a dedicated Claude CLI session, never
silently resume or inject work into an unrelated existing session. Begin with
read-only review to avoid concurrent edits in this currently uncommitted tree.
