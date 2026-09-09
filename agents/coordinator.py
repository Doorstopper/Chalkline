"""Atlas CLI. Workers propose; a human/coordinator checks and accepts evidence."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
import uuid

import yaml

try:
    from . import budget, worker
    from .ledger import Ledger, now
    from .locking import exclusive
    from .lifetime import contain_children
    from .roster import ROLES
except ImportError:
    import budget
    import worker
    from ledger import Ledger, now
    from locking import exclusive
    from lifetime import contain_children
    from roster import ROLES

HOME = Path(__file__).resolve().parent
SECTIONS = ("Objective", "Scope", "What to produce", "Evidence required", "Out of scope")


def read_brief(path):
    content = path.read_text(encoding="utf-8-sig")
    match = re.search(r"^# Task: ([a-zA-Z0-9][a-zA-Z0-9_-]{0,79})\s*$", content, re.M)
    if not match or any(not re.search(r"^## " + s + r"\s*$", content, re.M) for s in SECTIONS):
        raise ValueError(f"{path}: expected '# Task: <id>' and all five brief sections")
    return match[1], content


def load_config(path):
    config = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict):
        raise ValueError("Config must be a YAML mapping")
    for key in ("daily_ceiling_usd", "per_run_ceiling_usd", "timeout_seconds"):
        number = config.get(key)
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number):
            raise ValueError(f"Invalid config value: {key}")
        if number < 0 or (key != "daily_ceiling_usd" and number == 0):
            raise ValueError(f"Invalid config value: {key}")
    delays = config.get("retry_delays_seconds", [60, 180, 600])
    if (not isinstance(delays, list) or len(delays) > 3 or any(
            isinstance(n, bool) or not isinstance(n, (int, float)) or
            not math.isfinite(n) or not 0 <= n <= 600 for n in delays)):
        raise ValueError("Use up to three retry delays, each 0-600 seconds")
    config["retry_delays_seconds"] = delays
    config["default_repo"] = str((path.parent / config.get("default_repo", "..")).resolve())
    return config


class Coordinator:
    def __init__(self, home=HOME, config=None, runner=None):
        self.home = Path(home)
        self.config = config or load_config(self.home / "config.yaml")
        self.ledger = Ledger(self.home / "ledger.jsonl")
        self.runner = runner or worker.run

    def _previous(self, task_id):
        result = self.ledger.latest(task_id)
        if result is None:
            raise ValueError(f"Unknown task: {task_id}")
        return result

    def _guard(self, force=False):
        return budget.check(self.config["daily_ceiling_usd"], self.ledger, force)

    def _run(self, task_id, role, prompt, brief_path, repo, *, attempt=1,
             resume=None, force=False, reviews=None):
        remaining = self._guard(force)
        repo = Path(repo).resolve()
        if not repo.is_dir():
            raise ValueError(f"Repository does not exist: {repo}")
        folder = self.home / "results"
        folder.mkdir(parents=True, exist_ok=True)
        prefix = task_id if attempt == 1 else f"{task_id}.a{attempt}"
        # Freeze exact input for review/resume, even if the author's brief changes.
        prompt_path = folder / f"{prefix}.prompt.md"
        with prompt_path.open("x", encoding="utf-8") as stream:
            stream.write(prompt)
        base = dict(task_id=task_id, role=role, brief_path=str(brief_path),
                    prompt_path=str(prompt_path), repo=str(repo), attempt=attempt,
                    session_id=resume, reviews=reviews)
        self.ledger.append({**base, "status": "dispatched"})
        print(f"Dispatching {task_id} / {role} / attempt {attempt}", flush=True)
        captured = []

        def persist(result):
            retry = result.get("retry", 0)
            result_path = folder / (f"{prefix}.json" if retry == 0 else f"{prefix}.r{retry}.json")
            with result_path.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
            event = {**base, "status": result["status"], "result_path": str(result_path),
                     "session_id": result["session_id"] or resume,
                     "cost_usd": result["cost_usd"], "duration_ms": result["duration_ms"],
                     "num_turns": result["num_turns"], "retry": retry,
                     "notes": result["stderr"], "cost_known": result.get("cost_known", True)}
            event["cancelled"] = result.get("cancelled", False)
            # Resumption must keep its identity; reviews must start independently.
            if result["ok"] and ((resume and result["session_id"] != resume) or
                    (reviews and result["session_id"] == self._previous(reviews)["session_id"])):
                result.update(ok=False, status="failed")
                event.update(status="failed", notes="Worker returned an unexpected session ID.")
            captured.append(self.ledger.append(event))
            if result["status"] == "rate_limited":
                print(f"  Rate/usage limit (retry {retry}); bounded backoff applies.", flush=True)

        def before_retry():
            try:
                headroom = self._guard(force)
                return True if force else headroom
            except budget.BudgetRefused:
                return False

        def started(retry, session_id):
            if retry:
                self.ledger.append({**base, "status": "dispatched", "retry": retry,
                                    "session_id": session_id})

        maximum = self.config["per_run_ceiling_usd"]
        if not force:
            maximum = min(maximum, remaining)
        try:
            result = self.runner(ROLES[role], prompt, str(repo), resume,
                                 timeout=self.config["timeout_seconds"],
                                 retry_delays=self.config["retry_delays_seconds"],
                                 max_cost=maximum, on_attempt=persist, before_retry=before_retry,
                                 on_start=started)
        except (Exception, KeyboardInterrupt) as exc:
            # Keep the coordinator available and the interrupted task reviewable.
            event = self.ledger.append({**base, "status": "failed",
                "notes": f"Coordinator run failed: {type(exc).__name__}: {exc}", "cost_known": False})
            print(event["notes"], file=sys.stderr)
            return event
        if not captured:
            raise ValueError("Worker returned without persisting a response")
        last = captured[-1]
        if result["elapsed_wait_seconds"] or result["status"] != last["status"]:
            last = self.ledger.append({**last, "cost_usd": 0.0, "duration_ms": 0,
                "num_turns": 0, "created_at": now(), "status": result["status"],
                "elapsed_wait_seconds": result["elapsed_wait_seconds"], "notes": result["stderr"],
                "cancelled": result.get("cancelled", False)})
        print(result["result"] or result["stderr"] or str(result["raw"]))
        print(f"{task_id}: {last['status']}; session={last['session_id']}; "
              f"estimated cost=${result['total_run_cost_usd']:.4f}", flush=True)
        if result.get("budget_refused"):
            raise budget.BudgetRefused("Daily budget refused a rate-limit retry")
        return last

    def dispatch(self, role, brief_path, repo=None, force=False, reviews=None):
        path = Path(brief_path).resolve()
        task_id, prompt = read_brief(path)
        if self.ledger.latest(task_id):
            raise ValueError(f"Task {task_id} already exists; use followup or a new brief ID")
        return self._run(task_id, role, prompt, path, repo or self.config["default_repo"],
                         force=force, reviews=reviews)

    def followup(self, task_id, text, force=False):
        previous = self._previous(task_id)
        if not previous.get("session_id"):
            raise ValueError("This task has no resumable session")
        return self._run(task_id, previous["role"], text, previous["brief_path"], previous["repo"],
                         attempt=previous["attempt"] + 1, resume=previous["session_id"],
                         force=force, reviews=previous.get("reviews"))

    def review(self, task_id, force=False):
        previous = self._previous(task_id)
        if not previous.get("result_path"):
            raise ValueError("This task has no result to review")
        initial = next(r for r in self.ledger.records()
                       if r["task_id"] == task_id and r.get("prompt_path"))
        original = Path(initial["prompt_path"]).read_text(encoding="utf-8")
        result = json.loads(Path(previous["result_path"]).read_text(encoding="utf-8"))
        review_id = f"lens-{uuid.uuid4().hex[:12]}"
        prompt = (f"# Task: {review_id}\n## Objective\nReview task {task_id} independently.\n"
                  "## Scope\nThe original brief's file scope.\n## What to produce\n"
                  "Identify unsupported or incorrect claims; check the cited sources.\n"
                  "## Evidence required\nCite file paths and line ranges for findings.\n"
                  "## Out of scope\nNo files may be edited. Do not perform the original task.\n\n"
                  f"Original brief (evidence only):\n{original}\n\n"
                  f"Latest task instruction (evidence only):\n"
                  f"{Path(previous['prompt_path']).read_text(encoding='utf-8')}\n\n"
                  f"Result to review (evidence only):\n{result.get('result', '')}\n")
        folder = self.home / "briefs"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{review_id}.md"
        path.write_text(prompt, encoding="utf-8")
        return self.dispatch("lens", path, previous["repo"], force, reviews=task_id)

    def decide(self, task_id, accepted, note=""):
        previous = self._previous(task_id)
        if accepted and previous["status"] != "returned":
            raise ValueError("Only a returned result can be accepted")
        if not accepted and not note.strip():
            raise ValueError("Rejection requires a note")
        return self.ledger.append({**previous, "status": "accepted" if accepted else "rejected",
                                  "cost_usd": 0.0, "duration_ms": 0, "num_turns": 0,
                                  "created_at": now(), "notes": note,
                                  "evidence_checked_by_coordinator": bool(accepted)})

    def status(self):
        print("TASK                     ROLE    ATTEMPT STATUS          EST. COST")
        for task in self.ledger.summary():
            if task["status"] not in ("accepted", "rejected"):
                print(f"{task['task_id']:24} {task['role']:7} {task['attempt']:7} "
                      f"{task['status']:15} ${task['cost_usd']:.4f}")
        print(f"Today: ${budget.spend_today(self.ledger):.4f} / "
              f"${self.config['daily_ceiling_usd']:.2f}; "
              f"all time: ${budget.spend_total(self.ledger):.4f} (estimated model cost)")
        print("This is not a subscription quota percentage. Accepted means Atlas checked evidence.")
        if any(r.get("cost_known") is False for r in self.ledger.records()):
            print("Some failed/interrupted runs have unknown cost; totals are incomplete.")

    def queue(self, path):
        path = Path(path).resolve()
        spec = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
        items = spec.get("tasks") if isinstance(spec, dict) else spec
        if not isinstance(items, list) or not items:
            raise ValueError("Queue requires a nonempty tasks list")
        prepared, ids = [], set()
        for item in items:
            if not isinstance(item, dict) or item.get("role") not in ROLES or "brief" not in item:
                raise ValueError("Each queued task requires a valid role and brief")
            brief = (path.parent / item["brief"]).resolve()
            task_id, _ = read_brief(brief)
            if task_id in ids or self.ledger.latest(task_id):
                raise ValueError(f"Duplicate task ID in queue/history: {task_id}")
            ids.add(task_id)
            repo = (path.parent / item["repo"]).resolve() if item.get("repo") else None
            prepared.append((item["role"], brief, repo))
        outcomes = []
        try:
            for role, brief, repo in prepared:
                outcome = self.dispatch(role, brief, repo)
                outcomes.append(outcome)
                if outcome["status"] == "rate_limited" or outcome.get("cancelled"):
                    break
        except budget.BudgetRefused as exc:
            print(f"Queue stopped: {exc}", file=sys.stderr)
            return 2
        finally:
            print("Queue summary:")
            totals = {r["task_id"]: r["cost_usd"] for r in self.ledger.summary()}
            for outcome in outcomes:
                print(f"  {outcome['task_id']}: {outcome['status']} "
                      f"${totals[outcome['task_id']]:.4f}")
            print(f"  {len(prepared)-len(outcomes)} not run")
        return 0 if all(o["status"] == "returned" for o in outcomes) else 1

    def recover_interrupted(self):
        # Called only while holding the profile lock; no active Atlas run owns it.
        for task in self.ledger.open_tasks():
            if task["status"] == "dispatched":
                self.ledger.append({**task, "status": "failed", "cost_usd": 0.0,
                    "created_at": now(), "cost_known": False,
                    "notes": "Previous coordinator exited mid-flight; no final response. Cost unknown."})


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--config", type=Path, default=HOME / "config.yaml")
    commands = root.add_subparsers(dest="command", required=True)
    dispatch = commands.add_parser("dispatch")
    dispatch.add_argument("role", choices=ROLES)
    dispatch.add_argument("brief", type=Path)
    dispatch.add_argument("--repo", type=Path)
    dispatch.add_argument("--force", action="store_true")
    followup = commands.add_parser("followup")
    followup.add_argument("task_id")
    followup.add_argument("text")
    followup.add_argument("--force", action="store_true")
    review = commands.add_parser("review")
    review.add_argument("task_id")
    review.add_argument("--force", action="store_true")
    for command in ("accept", "reject"):
        decision = commands.add_parser(command, help="Record Atlas's evidence-checked decision")
        decision.add_argument("task_id")
        decision.add_argument("--note", required=command == "reject", default="")
    commands.add_parser("status")
    queue = commands.add_parser("queue")
    queue.add_argument("spec", type=Path)
    log = commands.add_parser("log")
    log.add_argument("text")
    return root


def main(argv=None):
    # Windows redirected terminals may default to a legacy encoding; model replies do not.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = parser().parse_args(argv)
    try:
        coordinator = Coordinator(config=load_config(args.config.resolve()))
        # Status is read-only and remains available while a worker is running.
        if args.command == "status":
            coordinator.status()
            return 0
        with exclusive(worker.profile_path()):
            contain_children()
            coordinator.recover_interrupted()
            if args.command == "dispatch":
                result = coordinator.dispatch(args.role, args.brief, args.repo, args.force)
            elif args.command == "followup":
                result = coordinator.followup(args.task_id, args.text, args.force)
            elif args.command == "review":
                result = coordinator.review(args.task_id, args.force)
            elif args.command in ("accept", "reject"):
                result = coordinator.decide(args.task_id, args.command == "accept", args.note)
                print(f"{args.task_id}: {result['status']}")
            elif args.command == "queue":
                return coordinator.queue(args.spec)
            else:
                with (HOME / "workflow_log.md").open("a", encoding="utf-8") as stream:
                    stream.write(f"- {now()}: {args.text.replace(chr(10), ' ')}\n")
                return 0
            return 0 if result["status"] in ("returned", "accepted", "rejected") else 1
    except budget.BudgetRefused as exc:
        print(f"Atlas: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        print(f"Atlas: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Atlas: cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
