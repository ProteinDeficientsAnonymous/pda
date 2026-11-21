#!/usr/bin/env python3
"""PostToolUse hook: after an agent's `git push` / `gh pr create`, remind it to watch CI and fix failures."""

from __future__ import annotations

import fnmatch
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


shell_parse = _load_module("shell_parse", Path(__file__).with_name("shell_parse.py"))
push_dir = shell_parse.push_dir

# mirrors the push branches in .github/workflows/ci.yml; fnmatch's * also matches "/"
CI_PUSH_BRANCHES = ("main", "claude/*", "feat-*", "fix-*", "chore-*")


def current_branch(where: Path) -> str:
    if not where.is_dir():
        return ""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=where,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def creates_pr(command: str) -> bool:
    return any(seg[:3] == ["gh", "pr", "create"] for seg in shell_parse.segments(command))


def has_open_pr(where: Path) -> bool:
    try:
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "state", "--jq", ".state"],
            cwd=where,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "OPEN"


def ci_runs(command: str, where: Path, branch: str) -> bool:
    if creates_pr(command):
        return True
    if any(fnmatch.fnmatchcase(branch, pattern) for pattern in CI_PUSH_BRANCHES):
        return True
    return where.is_dir() and has_open_pr(where)


def reminder(branch: str) -> str:
    pushed = f"`{branch}`" if branch else "this branch"
    return (
        f"You pushed {pushed}; GitHub CI is now running on it. Watch the run until every check "
        "finishes (`gh pr checks --watch` with a PR, `gh run watch` without, or subscribe to the "
        "PR's activity), then fix any "
        "failure at its cause, commit, and push again. Do not suppress, skip, or weaken tests to "
        "get green; if a failure looks unrelated or flaky, say so instead of declaring the work done."
    )


def output(event: dict) -> dict | None:
    command = (event.get("tool_input") or {}).get("command") or ""
    where = push_dir(command, Path(event.get("cwd") or "."))
    if where is None:
        return None
    branch = current_branch(where)
    if not ci_runs(command, where, branch):
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": reminder(branch),
        }
    }


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    if result := output(event):
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
