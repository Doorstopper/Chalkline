# Atlas local coordinator

Atlas is the lead workflow run by Codex. Scout, Bolt and Lens are read-only Claude Code workers using one subscription and a dedicated authenticated profile. This CLI dispatches their tasks and records results; it is not an unattended Codex service and does not automatically verify or accept model claims.

## Launch

From the Chalkline repository in PowerShell:

```powershell
.\agents\atlas.ps1 status
.\agents\atlas.ps1 dispatch scout agents/briefs/my-task.md
.\agents\atlas.ps1 followup my-task "Check the error paths too"
.\agents\atlas.ps1 review my-task
.\agents\atlas.ps1 accept my-task --note "Checked the cited source and ran the relevant verification"
.\agents\atlas.ps1 reject my-task --note "The cited test does not exercise the reported failure"
.\agents\atlas.ps1 queue agents/briefs/queue.yaml
.\agents\atlas.ps1 log "A narrow brief reduced unnecessary reading"
```

The direct entry point is `python agents/coordinator.py`. `--help` lists commands. The supplied `briefs/t001.md` is the setup smoke task; use a new ID for new work. Copy `briefs/template.md` and give it a unique ID. Existing IDs cannot be dispatched again; use followup to preserve their history and session.

`accept` is Atlas's explicit attestation that the evidence was checked. A model report, a green status, or a second model agreeing is not sufficient verification. Inspect cited source and perform the relevant checks before recording acceptance. Acceptance changes status only; it never applies proposed patches.

## Runtime and account

Python 3.10+ and `PyYAML>=6,<7` are the only Python requirements. This workstation uses `E:\Chalkline\development-runtime\Scripts\python.exe`; PyYAML 6.0.3 is installed. The launcher also supports `ATLAS_PYTHON`, an `agents/.venv`, or Python on PATH. For an independent installation, create a venv and install `agents/requirements.txt`.

Claude discovery: `ATLAS_CLAUDE_BIN`, then PATH, then the newest installed VS Code Claude extension's native binary. No duplicate global installation is required. Set the override if your installation lives elsewhere.

`ATLAS_CONFIG_DIR` defaults to `~/.claude-atlas`. Sign-in to this dedicated profile was completed and verified on 2026-09-08 with the existing Claude Max account. All roles share it. Auth stays outside this repository. Child environments copy the parent, set `CLAUDE_CONFIG_DIR`, and remove inherited Anthropic API/provider overrides so subscription login is used. The parent environment is unchanged.

## Roster and permissions

| Role | Model | Maximum turns |
| --- | --- | --- |
| Scout | `claude-fable-5-1` | 30 |
| Bolt | `claude-opus-5` | 10 |
| Lens | `claude-fable-5-1` | 20 |

Every invocation reapplies the model, turn ceiling, system prompt and permissions. New dispatches start fresh sessions. Followups use the named task's session. Reviews get a new task ID and fresh Lens session, plus the saved original brief, latest instruction and latest result. A mismatched session identity fails the run.

**Deliberate tightening of the supplied brief:** workers have `Read,Grep,Glob` only. `--tools` restricts availability; `--allowedTools` approves those tools; `--permission-mode dontAsk` denies other permission requests. Safe/restricted mode disables customizations and confines file tools to working directories. MCP, Chrome and slash commands are disabled. No bypass-permissions flag is used.

The brief's broad `Bash(git diff:*)` rule could permit output files or external helpers. Atlas instead performs Git inspection and tests itself, supplying only relevant evidence to workers. Scope discipline is still required: read-only access does not make every file in a repository appropriate to share with a service. The Claude CLI itself writes session/auth state to its profile; read-only refers to workers' access to the repository under review.

## Costs, retries and serialization

`config.yaml` starts with a **$5 daily estimated-cost ceiling**, **$1 per invocation ceiling**, 600-second timeout, and rate-limit waits of 60/180/600 seconds. Change these values locally as needed. `--config PATH` selects another config file.

Claude's reported model cost is an estimate, not a subscription percentage or a statement of additional billed charges. Atlas cannot monitor or guarantee the requested 60% stop point in a five-hour allowance. Chad must check the account usage meter between bounded packets. These limits also exclude interactive Claude usage and work done before this ledger was created.

Cost is written once per actual CLI response. Acceptance, rejection and wait summary events carry zero cost. Status shows today's local-time spend and all-time spend. Missing cost metadata on interrupted/failed runs is flagged as unknown. Budget checks run before dispatch, followup, review and retries. `--force` bypasses the daily guard for that command only; the per-invocation cap still applies. The CLI's cost cap can overshoot by an in-flight request; it is not a billing cap.

Only explicit rate/usage-limit errors trigger retries. Model/auth/task failures, malformed output, timeout and interruption fail immediately. Ctrl+C cancels a run or its backoff. All retry responses are saved, including stderr and partial output. The Windows/POSIX profile lock serializes Atlas commands across processes, and a queue holds it throughout. `status` remains available while a run is active. This lock cannot control other apps using the same subscription.

A hard termination of the coordinator cannot produce a final response. On Windows, `lifetime.py` places Atlas and its children in a private job so a forcibly killed coordinator cannot leave a Claude worker running. On the next mutating command, abandoned dispatched events are recorded as failed with unknown cost. This containment is tested on this workstation. On other operating systems, inspect child processes before restarting after a forced kill.

## Files and queue format

`roster.py`, `worker.py`, `ledger.py`, `budget.py` and `coordinator.py` are the core; `locking.py` handles cross-process serialization and `lifetime.py` handles Windows process containment. Tests live in `tests/`, temporary work in ignored `scratch/`, task inputs in `briefs/`, and responses in ignored `results/`. `ledger.jsonl` is append-only and gitignored. Do not edit it during a run.

Raw response envelopes contain the original JSON under `raw`, exact stdout and stderr, plus normalized fields. First runs use `<task>.json`; followups use `<task>.a2.json`, and retries add `.r1`. Exact prompts are saved alongside them so later edits to a brief cannot silently change what a reviewer sees.

```yaml
tasks:
  - role: scout
    brief: investigate.md
  - role: bolt
    brief: narrow-check.md
    repo: ../..
  - role: lens
    brief: independent-check.md
```

Queue paths are relative to the YAML file. Dispatch paths are relative to the terminal. The default repo in config is relative to the config file. Queues run in order and stop at rate-limit exhaustion or budget refusal; other failures are reported and subsequent tasks continue. `review <id>` is the command that automatically attaches the original brief/result and records the `reviews` link.

## Verification

```powershell
& 'E:\Chalkline\development-runtime\Scripts\python.exe' -B -m unittest discover -s agents/tests -v
```

Tests mock Claude and also terminate local test-only Python processes: they consume no subscription usage. Live setup results are separate ledger entries. See `workflow_log.md` for checked results.

Implementation references: [Claude CLI reference](https://code.claude.com/docs/en/cli-reference), the installed CLI's `--help` (2.1.263), and [Microsoft's job object documentation](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects). Model names match the supplied brief. Chalkline's PWA and native source are unchanged by this setup.
