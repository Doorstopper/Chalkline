"""Bounded Claude subprocesses; no shell, edits, hooks, or automatic acceptance."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time


def profile_path() -> Path:
    return Path(os.environ.get("ATLAS_CONFIG_DIR", "~/.claude-atlas")).expanduser().resolve()


def find_claude() -> str:
    override = os.environ.get("ATLAS_CLAUDE_BIN")
    if override:
        return str(Path(override).expanduser())
    found = shutil.which("claude")
    if found:
        return found
    # VS Code already bundles a native CLI on this workstation.
    candidates = list((Path.home() / ".vscode/extensions").glob(
        "anthropic.claude-code-*/resources/native-binary/claude.exe"))
    def version(path):
        return tuple(int(n) for n in re.findall(r"\d+", path.parents[2].name))
    if candidates:
        return str(max(candidates, key=version))
    return "claude"  # A missing executable becomes a normal failed result.


def construction(role, prompt, cwd, resume=None, *, timeout=600, max_cost=None):
    if role.allowed_tools != "Read,Grep,Glob":
        raise ValueError("Atlas workers may only use Read,Grep,Glob")
    env = os.environ.copy()
    env["CLAUDE_CONFIG_DIR"] = str(profile_path())
    # Use the signed-in subscription, never an inherited API key/provider.
    for key in list(env):
        if key.startswith("ANTHROPIC_") or key.startswith("CLAUDE_CODE_USE_"):
            del env[key]
    env.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
    env.pop("CLAUDE_CONFIG_DIR_OVERRIDE", None)
    argv = [find_claude(), "-p", prompt, "--output-format", "json",
            "--model", role.model, "--max-turns", str(role.max_turns),
            "--allowedTools", role.allowed_tools,
            "--append-system-prompt", role.role_prompt,
            "--tools", "Read,Grep,Glob", "--permission-mode", "dontAsk",
            "--safe-mode", "--restricted", "--strict-mcp-config",
            "--mcp-config", '{"mcpServers":{}}', "--no-chrome",
            "--disable-slash-commands"]
    if resume:
        argv += ["--resume", resume]
    if max_cost is not None:
        argv += ["--max-budget-usd", str(max_cost)]
    return argv, dict(cwd=str(Path(cwd).resolve()), env=env,
                      capture_output=True, text=True, encoding="utf-8",
                      errors="replace", timeout=timeout)


def _text(value):
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else (value or "")


def _number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) and number >= 0 else 0.0
    except (ValueError, TypeError):
        return 0.0


def _once(argv, kwargs):
    started = time.monotonic()
    stdout, stderr, exit_code = "", "", -1
    cancelled = False
    try:
        completed = subprocess.run(argv, **kwargs)
        stdout, stderr, exit_code = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = _text(exc.stdout)
        stderr = _text(exc.stderr) + "\nAtlas: worker timeout; subprocess terminated."
    except KeyboardInterrupt:
        stderr = "Atlas: worker interrupted by operator."
        cancelled = True
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        stderr = f"Atlas: {type(exc).__name__}: {exc}"
    try:
        raw = json.loads(stdout)
        if not isinstance(raw, dict):
            raise ValueError("expected a JSON object")
    except (ValueError, TypeError):
        raw = {"unparsed_stdout": stdout}
        stderr += "\nAtlas: no valid JSON result object."
    ok = (exit_code == 0 and raw.get("type") == "result"
          and not raw.get("is_error") and bool(raw.get("session_id")))
    error_text = " ".join(str(raw.get(k, "")) for k in
                          ("subtype", "error", "errors", "result")) + " " + stderr
    ordinary_failure = raw.get("subtype") in ("error_max_turns", "error_max_budget_usd",
                                               "error_max_structured_output_retries")
    rate_limited = not ok and not ordinary_failure and bool(re.search(
        r"rate[_ -]?limit|usage[_ -]?limit|quota exceeded|hit your limit|"
        r"too many requests|\b429\b", error_text, re.I))
    return dict(ok=ok, result=raw.get("result", ""), session_id=raw.get("session_id"),
                cost_usd=_number(raw.get("total_cost_usd")),
                duration_ms=int(_number(raw.get("duration_ms", (time.monotonic()-started)*1000))),
                num_turns=int(_number(raw.get("num_turns"))), exit_code=exit_code,
                stderr=stderr.strip(), raw=raw, stdout=stdout,
                status="returned" if ok else "rate_limited" if rate_limited else "failed",
                cost_known="total_cost_usd" in raw, cancelled=cancelled)


def run(role, prompt: str, cwd: str, resume: str | None = None, *,
        timeout=600, retry_delays=(60, 180, 600), max_cost=None,
        on_attempt=None, before_retry=None, on_start=None, sleep=None) -> dict:
    """Return every raw attempt; retry only explicit rate/usage-limit errors.

    Callbacks let the coordinator persist cost immediately and guard each retry.
    A retry resumes a returned session ID to avoid repeating completed tool work.
    """
    attempts, waited = [], 0.0
    sleep = sleep or time.sleep
    current_resume = resume
    for retry in range(len(retry_delays) + 1):
        try:
            if on_start:
                on_start(retry, current_resume)
            argv, kwargs = construction(role, prompt, cwd, current_resume,
                                        timeout=timeout, max_cost=max_cost)
            result = _once(argv, kwargs)
        except (OSError, ValueError) as exc:
            result = dict(ok=False, result="", session_id=None, cost_usd=0.0,
                          duration_ms=0, num_turns=0, exit_code=-1,
                          stderr=str(exc), raw={}, stdout="", status="failed", cost_known=False)
        result["retry"] = retry
        attempts.append(result)
        if on_attempt:
            on_attempt(result)
        if result["status"] != "rate_limited" or retry == len(retry_delays):
            break
        if before_retry:
            allowance = before_retry()
            if allowance is False:
                result = {**result, "ok": False, "status": "failed",
                          "stderr": result["stderr"] + "\nAtlas: budget refused retry.",
                          "budget_refused": True}
                break
            if isinstance(allowance, (int, float)) and not isinstance(allowance, bool):
                max_cost = min(max_cost if max_cost is not None else allowance, allowance)
        current_resume = result["session_id"] or current_resume
        remaining = retry_delays[retry]
        try:
            while remaining > 0:
                chunk = min(1.0, remaining)
                sleep(chunk)
                waited += chunk
                remaining -= chunk
        except KeyboardInterrupt:
            result = {**result, "ok": False, "status": "failed",
                      "stderr": result["stderr"] + "\nAtlas: retry wait interrupted.", "cancelled": True}
            break
    return {**result, "attempts": attempts, "elapsed_wait_seconds": waited,
            "total_run_cost_usd": sum(r["cost_usd"] for r in attempts)}
