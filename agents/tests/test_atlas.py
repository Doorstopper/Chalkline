"""Offline acceptance tests: no account access or model usage."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agents import budget, worker
from agents.coordinator import Coordinator, load_config
from agents.ledger import Ledger
from agents.locking import exclusive
from agents.roster import ROLES


def response(session="session-1", cost=0.1, *, error=False, result="Evidence: file.py:1", code=0):
    return subprocess.CompletedProcess([], code, json.dumps(dict(
        type="result", is_error=error, result=result, session_id=session,
        total_cost_usd=cost, duration_ms=12, num_turns=1)), "")


class AtlasTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = dict(daily_ceiling_usd=5, per_run_ceiling_usd=1,
                           timeout_seconds=10, retry_delays_seconds=[], default_repo=str(self.root))
        self.coordinator = Coordinator(self.root, self.config)
        self.output = io.StringIO()
        self.redirect = redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)

    def brief(self, task="t001"):
        path = self.root / f"{task}.md"
        path.write_text(f"# Task: {task}\n## Objective\nCheck a fact.\n## Scope\nfile.py\n"
                        "## What to produce\nFinding.\n## Evidence required\nPaths and lines.\n"
                        "## Out of scope\nNo files may be edited.\n", encoding="utf-8")
        return path

    def test_dispatch_followup_fresh_review_and_frozen_brief(self):
        brief = self.brief()
        with patch.object(worker.subprocess, "run", side_effect=[response(), response(), response("review-1")]) as invoke:
            first = self.coordinator.dispatch("scout", brief)
            followup = self.coordinator.followup("t001", "check the error paths too")
            brief.write_text("Changed after dispatch", encoding="utf-8")
            review = self.coordinator.review("t001")
        self.assertEqual(first["status"], "returned")
        self.assertGreater(first["cost_usd"], 0)
        self.assertEqual(followup["attempt"], 2)
        self.assertEqual(first["session_id"], followup["session_id"])
        self.assertNotEqual(review["session_id"], first["session_id"])
        self.assertEqual(review["reviews"], "t001")
        calls = [c.args[0] for c in invoke.call_args_list]
        self.assertNotIn("--resume", calls[0])
        self.assertEqual(calls[1][calls[1].index("--resume") + 1], "session-1")
        self.assertNotIn("--resume", calls[2])
        self.assertIn("Check a fact.", calls[2][2])
        self.assertIn("check the error paths too", calls[2][2])
        self.assertNotIn("Changed after dispatch", calls[2][2])
        self.assertTrue(Path(first["result_path"]).exists())
        self.assertNotEqual(first["result_path"], followup["result_path"])

    def test_queue_runs_in_order(self):
        for name in ("q1", "q2", "q3"):
            self.brief(name)
        queue = self.root / "queue.yaml"
        queue.write_text("tasks:\n" + "".join(f"  - role: bolt\n    brief: {n}.md\n" for n in ("q1", "q2", "q3")))
        active, order = 0, []
        def fake(argv, **kwargs):
            nonlocal active
            active += 1
            self.assertEqual(active, 1)
            order.append(argv[2].splitlines()[0])
            active -= 1
            return response(f"s{len(order)}")
        with patch.object(worker.subprocess, "run", side_effect=fake):
            self.assertEqual(self.coordinator.queue(queue), 0)
        self.assertEqual(order, ["# Task: q1", "# Task: q2", "# Task: q3"])
        self.assertIn("0 not run", self.output.getvalue())

    def test_rate_limit_backoff_and_queue_stop(self):
        self.config["retry_delays_seconds"] = [60, 180, 600]
        queue = self.root / "queue.yaml"
        self.brief("r1")
        self.brief("r2")
        queue.write_text("tasks:\n  - role: scout\n    brief: r1.md\n  - role: bolt\n    brief: r2.md\n")
        with patch.object(worker.subprocess, "run", return_value=response(error=True, result="usage limit reached", code=1)) as invoke, \
                patch.object(worker.time, "sleep") as sleep:
            self.assertEqual(self.coordinator.queue(queue), 1)
        self.assertEqual(invoke.call_count, 4)
        self.assertEqual(sum(c.args[0] for c in sleep.call_args_list), 840)
        last = self.coordinator.ledger.latest("r1")
        self.assertEqual(last["status"], "rate_limited")
        self.assertEqual(last["elapsed_wait_seconds"], 840)
        self.assertIsNone(self.coordinator.ledger.latest("r2"))
        self.assertEqual(len(list((self.root / "results").glob("*.json"))), 4)
        self.assertAlmostEqual(budget.spend_total(self.coordinator.ledger), 0.4)

    def test_budget_force_and_status_do_not_double_count(self):
        with patch.object(worker.subprocess, "run", return_value=response()):
            self.coordinator.dispatch("bolt", self.brief())
            self.coordinator.decide("t001", True, "Checked file.py:1")
            self.assertAlmostEqual(budget.spend_total(self.coordinator.ledger), 0.1)
            self.assertAlmostEqual(budget.spend_today(self.coordinator.ledger), 0.1)
            self.config["daily_ceiling_usd"] = 0.05
            with self.assertRaises(budget.BudgetRefused):
                self.coordinator.dispatch("bolt", self.brief("t002"))
            self.coordinator.dispatch("bolt", self.brief("t003"), force=True)
            with self.assertRaises(budget.BudgetRefused):
                self.coordinator.dispatch("bolt", self.brief("t004"))
        self.assertAlmostEqual(budget.spend_total(self.coordinator.ledger), 0.2)

    def test_timeout_killed_process_and_bad_json_are_failed(self):
        failures = [subprocess.TimeoutExpired("claude", 10, output=b"partial", stderr=b"diagnostic"),
                    subprocess.CompletedProcess([], -9, "", "terminated externally"),
                    subprocess.CompletedProcess([], 0, "not json", "bad output")]
        for index, failure in enumerate(failures):
            with patch.object(worker.subprocess, "run", side_effect=[failure]) as invoke:
                result = self.coordinator.dispatch("bolt", self.brief(f"fail{index}"))
            self.assertEqual(result["status"], "failed")
            self.assertTrue(result["notes"])
            self.assertEqual(invoke.call_count, 1)
        self.assertEqual(len(self.coordinator.ledger.open_tasks()), 3)

    def test_read_only_flags_and_child_environment_on_resume(self):
        original_env = dict(os.environ)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "not-a-real-key", "ATLAS_CONFIG_DIR": str(self.root)}):
            with patch.object(worker.subprocess, "run", return_value=response(result="I cannot edit files.")) as invoke:
                result = worker.run(ROLES["bolt"], "Write hacked.txt", str(self.root), "session-1")
            argv, kwargs = invoke.call_args.args[0], invoke.call_args.kwargs
            self.assertEqual(argv[argv.index("--tools")+1], "Read,Grep,Glob")
            self.assertEqual(argv[argv.index("--allowedTools")+1], "Read,Grep,Glob")
            self.assertEqual(argv[argv.index("--permission-mode")+1], "dontAsk")
            self.assertIn("--safe-mode", argv)
            self.assertIn("--restricted", argv)
            self.assertIn("--strict-mcp-config", argv)
            self.assertNotIn("--dangerously-skip-permissions", argv)
            self.assertNotIn("ANTHROPIC_API_KEY", kwargs["env"])
            self.assertEqual(os.environ["ANTHROPIC_API_KEY"], "not-a-real-key")
            self.assertEqual(kwargs["env"]["CLAUDE_CONFIG_DIR"], str(self.root.resolve()))
            self.assertTrue(kwargs["capture_output"])
            self.assertGreater(kwargs["timeout"], 0)
            self.assertTrue(result["ok"])
        self.assertEqual(dict(os.environ), original_env)
        self.assertFalse((self.root / "hacked.txt").exists())

    def test_ordinary_error_mentioning_limits_is_not_retried_on_success(self):
        with patch.object(worker.subprocess, "run", return_value=response(result="The code handles rate limits")) as invoke:
            self.assertTrue(worker.run(ROLES["scout"], "inspect", str(self.root))["ok"])
            self.assertEqual(invoke.call_count, 1)
        with patch.object(worker.subprocess, "run", return_value=response(error=True, result="Invalid model", code=1)) as invoke:
            self.assertFalse(worker.run(ROLES["scout"], "inspect", str(self.root))["ok"])
            self.assertEqual(invoke.call_count, 1)

    def test_lock_excludes_second_coordinator_and_releases(self):
        with exclusive(self.root):
            with self.assertRaises(ValueError):
                with exclusive(self.root):
                    self.fail("second owner admitted")
        with exclusive(self.root):
            pass

    def test_mismatched_resume_is_failed(self):
        with patch.object(worker.subprocess, "run", side_effect=[response(), response("wrong-session")]):
            self.coordinator.dispatch("bolt", self.brief())
            result = self.coordinator.followup("t001", "follow up")
        self.assertEqual(result["status"], "failed")
        with self.assertRaises(ValueError):
            self.coordinator.decide("t001", True)

    def test_interrupted_coordinator_recovery_and_corrupt_ledger(self):
        ledger = self.coordinator.ledger
        ledger.append(dict(task_id="interrupted", status="dispatched"))
        self.coordinator.recover_interrupted()
        self.assertEqual(ledger.latest("interrupted")["status"], "failed")
        self.assertFalse(ledger.latest("interrupted")["cost_known"])
        with ledger.path.open("a") as stream:
            stream.write("{broken")
        with self.assertRaisesRegex(ValueError, "Ledger corruption"):
            self.coordinator._guard()

    def test_cancel_backoff_is_recorded(self):
        self.config["retry_delays_seconds"] = [60]
        with patch.object(worker.subprocess, "run", return_value=response(error=True, result="rate limit", code=1)), \
                patch.object(worker.time, "sleep", side_effect=KeyboardInterrupt):
            result = self.coordinator.dispatch("bolt", self.brief())
        self.assertEqual(result["status"], "failed")
        self.assertIn("interrupted", result["notes"])

    def test_retry_budget_refusal(self):
        self.config["retry_delays_seconds"] = [60]
        self.config["daily_ceiling_usd"] = 0.05
        with patch.object(worker.subprocess, "run", return_value=response(error=True, result="rate limit", code=1)) as invoke:
            with self.assertRaises(budget.BudgetRefused):
                self.coordinator.dispatch("bolt", self.brief())
        self.assertEqual(invoke.call_count, 1)

    def test_retry_cap_shrinks_with_remaining_daily_budget(self):
        self.config["daily_ceiling_usd"] = 0.3
        self.config["retry_delays_seconds"] = [0]
        with patch.object(worker.subprocess, "run", side_effect=[
                response(error=True, result="rate limit", code=1), response()]) as invoke:
            self.coordinator.dispatch("bolt", self.brief())
        argv = invoke.call_args_list[1].args[0]
        self.assertAlmostEqual(float(argv[argv.index("--max-budget-usd")+1]), 0.2)

    def test_turn_cap_failure_is_not_retried_for_task_text(self):
        reply = response(error=True, result="Investigating rate limits", code=1)
        raw = json.loads(reply.stdout)
        raw["subtype"] = "error_max_turns"
        reply.stdout = json.dumps(raw)
        with patch.object(worker.subprocess, "run", return_value=reply) as invoke:
            self.assertEqual(worker.run(ROLES["bolt"], "check", str(self.root))["status"], "failed")
        self.assertEqual(invoke.call_count, 1)

    def test_ctrl_c_stops_queue(self):
        self.brief("cancel1")
        self.brief("cancel2")
        path = self.root / "queue.yaml"
        path.write_text("tasks:\n  - role: bolt\n    brief: cancel1.md\n  - role: bolt\n    brief: cancel2.md\n")
        with patch.object(worker.subprocess, "run", side_effect=KeyboardInterrupt) as invoke:
            self.assertEqual(self.coordinator.queue(path), 1)
        self.assertEqual(invoke.call_count, 1)
        self.assertTrue(self.coordinator.ledger.latest("cancel1")["cancelled"])
        self.assertIsNone(self.coordinator.ledger.latest("cancel2"))

    def test_config_validation(self):
        path = self.root / "config.yaml"
        path.write_text("daily_ceiling_usd: .nan\nper_run_ceiling_usd: 1\ntimeout_seconds: 5")
        with self.assertRaises(ValueError):
            load_config(path)

    def test_cli_can_print_unicode_in_legacy_windows_encoding(self):
        code = ("from unittest.mock import patch; from agents.coordinator import Coordinator, main; "
                "patcher=patch.object(Coordinator,'status',lambda self: print(chr(0x2248))); "
                "patcher.start(); raise SystemExit(main(['status']))")
        result = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True,
                                timeout=10, env={**os.environ, 'PYTHONIOENCODING': 'ascii'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('\u2248', result.stdout.decode('utf-8'))

    def test_actual_terminated_process_is_recorded_and_next_task_runs(self):
        # A real local process exits via TerminateProcess/SIGTERM, not a mock exit code.
        code = "import os,signal,sys; print('termination diagnostic',file=sys.stderr,flush=True); os.kill(os.getpid(), signal.SIGTERM)"
        real_run = worker.subprocess.run
        def terminate_worker(argv, **kwargs):
            return real_run([sys.executable, "-c", code], **kwargs)
        with patch.object(worker.subprocess, "run", side_effect=terminate_worker):
            outcome = self.coordinator.dispatch("bolt", self.brief("killed"))
        self.assertEqual(outcome["status"], "failed")
        self.assertIn("termination diagnostic", outcome["notes"])
        with patch.object(worker.subprocess, "run", return_value=response()):
            self.assertEqual(self.coordinator.dispatch("bolt", self.brief("after-kill"))["status"], "returned")

    @unittest.skipUnless(os.name == "nt", "Windows process containment")
    def test_force_killed_coordinator_does_not_orphan_worker(self):
        import ctypes
        from ctypes import wintypes
        code = ("from agents.lifetime import contain_children; import subprocess,sys,time; "
                "contain_children(); child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'], "
                "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
                "print(child.pid,flush=True); time.sleep(30)")
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            subprocess.run([sys.executable, "-B", "-c", code], timeout=2,
                           capture_output=True, text=True)
        pid = int(caught.exception.stdout.strip())
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = api.OpenProcess(0x00100000, False, pid)
        if handle:
            try:
                self.assertEqual(api.WaitForSingleObject(handle, 3000), 0, "orphan worker is still running")
            finally:
                api.CloseHandle(handle)


if __name__ == "__main__":
    unittest.main()
