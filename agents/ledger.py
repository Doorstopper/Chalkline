"""Append-only task events. Status changes carry zero cost."""
from datetime import datetime
import json
import os
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "ledger.jsonl"


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


class Ledger:
    def __init__(self, path=DEFAULT_PATH):
        self.path = Path(path)

    def records(self):
        if not self.path.exists():
            return []
        records = []
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                item = json.loads(line)
                if not isinstance(item, dict) or "task_id" not in item:
                    raise ValueError("invalid event")
                records.append(item)
            except ValueError as exc:
                raise ValueError(f"Ledger corruption at {self.path}:{line_number}; "
                                 "dispatch refused; preserve the file for recovery.") from exc
        return records

    def append(self, record):
        event = dict(task_id="", role="", brief_path="", status="dispatched",
                     session_id=None, result_path="", cost_usd=0.0,
                     duration_ms=0, num_turns=0, attempt=1, created_at=now(), notes="")
        event.update(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return event

    def latest(self, task_id):
        return next((r for r in reversed(self.records()) if r["task_id"] == task_id), None)

    def open_tasks(self):
        latest = {r["task_id"]: r for r in self.records()}
        return [r for r in latest.values() if r["status"] not in ("accepted", "rejected")]

    def summary(self):
        tasks = {}
        for record in self.records():
            task = tasks.setdefault(record["task_id"], {"cost_usd": 0.0})
            cost = task["cost_usd"] + record["cost_usd"]
            task.update(record)
            task["cost_usd"] = cost
        return list(tasks.values())


def append(record):
    return Ledger().append(record)


def latest(task_id):
    return Ledger().latest(task_id)


def open_tasks():
    return Ledger().open_tasks()


def summary():
    return Ledger().summary()
