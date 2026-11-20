#!/usr/bin/env python3
"""PreToolUse hook: block an agent's `git push` / `gh pr create` while fast gates fail on the branch."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

MAX_ROUNDS = 3
OUTPUT_TAIL_LINES = 40
STATE_DIR = Path(tempfile.gettempdir()) / "pda-push-gate"
BASE_REFS = ("origin/main", "main")
CODE_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
PUSH = re.compile(
    r"(?:^|[;&|(]\s*|\s)(?:git(?:\s+-C\s+(?P<gitdir>\"[^\"]+\"|'[^']+'|\S+))?\s+push\b|gh\s+pr\s+create\b)"
)
CD = re.compile(r"(?:^|[;&|(]\s*)cd\s+(\"[^\"]+\"|'[^']+'|[^\s;&|]+)")
SKIP_PUSH_FLAGS = re.compile(r"\s(?:--delete|-d)\b")


@dataclass(frozen=True)
class Gate:
    name: str
    cmd: list[str]
    cwd: str
    env: tuple[tuple[str, str], ...] = ()


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def _unquote(token: str) -> str:
    return shlex.split(token)[0] if token else token


def push_dir(command: str, cwd: Path) -> Path | None:
    """return(Path | None): the directory a push in `command` runs from, or None when it doesn't push."""
    match = PUSH.search(command)
    if match is None or SKIP_PUSH_FLAGS.search(command[match.end() :].split("&&")[0]):
        return None
    where = cwd
    for cd in CD.finditer(command[: match.start() + 1]):
        where = (where / Path(_unquote(cd.group(1))).expanduser()).resolve()
    if match.group("gitdir"):
        where = (where / Path(_unquote(match.group("gitdir"))).expanduser()).resolve()
    return where


def merge_base(root: Path) -> str:
    return next((mb for ref in BASE_REFS if (mb := git(root, "merge-base", "HEAD", ref))), "HEAD")


def changed_files(root: Path) -> list[str]:
    committed = git(root, "diff", "--name-only", merge_base(root), "HEAD").splitlines()
    return sorted({p for p in committed if p and (root / p).is_file()})


def uncommitted(root: Path, files: list[str]) -> list[str]:
    dirty = set(git(root, "diff", "--name-only", "HEAD").splitlines())
    return [f for f in files if f in dirty]


def fingerprint(root: Path, files: list[str]) -> str:
    digest = hashlib.sha256()
    for rel in files:
        digest.update(rel.encode())
        digest.update((root / rel).read_bytes())
    return digest.hexdigest()


def select_gates(
    files: list[str], have_uv: bool, have_pnpm: bool, base: str = "HEAD"
) -> list[Gate]:
    backend = [
        f.removeprefix("backend/") for f in files if f.startswith("backend/") and f.endswith(".py")
    ]
    frontend = [
        f.removeprefix("frontend/")
        for f in files
        if f.startswith("frontend/")
        and f.endswith((".ts", ".tsx"))
        and not f.startswith("frontend/visual/")
    ]
    gates: list[Gate] = []
    if backend and have_uv:
        gates += [
            Gate("ruff check", ["uv", "run", "ruff", "check", *backend], "backend"),
            Gate("ruff format", ["uv", "run", "ruff", "format", "--check", *backend], "backend"),
            Gate("ty", ["make", "-s", "agent-typecheck"], "."),
            Gate(
                "affected pytest",
                ["make", "-s", "agent-test-since"],
                ".",
                env=(("TEST_BASE", base),),
            ),
        ]
    if frontend and have_pnpm:
        gates += [
            Gate("oxlint", ["pnpm", "exec", "oxlint", *frontend], "frontend"),
            Gate("oxfmt", ["pnpm", "exec", "oxfmt", "--check", *frontend], "frontend"),
            Gate("tsc", ["pnpm", "exec", "tsc", "-b", "--noEmit", "--pretty", "false"], "frontend"),
            Gate(
                "vitest related",
                ["pnpm", "exec", "vitest", "related", "--run", "--silent", *frontend],
                "frontend",
            ),
        ]
    return gates


def suppression_findings(root: Path, files: list[str]) -> list[str]:
    script = root / "scripts" / "check_anti_tampering.py"
    if not script.is_file():
        return []
    spec = importlib.util.spec_from_file_location("check_anti_tampering", script)
    if spec is None or spec.loader is None:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    code = [f for f in files if f.endswith(CODE_SUFFIXES)]
    return [
        hit
        for f in code
        for hit in mod.scan_text(f, (root / f).read_text(encoding="utf-8", errors="replace"))
    ]


def run_gate(root: Path, gate: Gate) -> str | None:
    result = subprocess.run(
        gate.cmd,
        cwd=root / gate.cwd,
        env={**os.environ, **dict(gate.env)},
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return None
    tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-OUTPUT_TAIL_LINES:])
    return f"## {gate.name} failed\n{tail}"


def load_state(session_id: str) -> dict:
    try:
        return json.loads((STATE_DIR / f"{session_id}.json").read_text())
    except (OSError, ValueError):
        return {}


def save_state(session_id: str, state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / f"{session_id}.json").write_text(json.dumps(state))


def repo_root(where: Path) -> Path | None:
    top = git(where, "rev-parse", "--show-toplevel") if where.is_dir() else ""
    return Path(top) if top else None


def _failures(root: Path, files: list[str]) -> list[str]:
    # gates read the working tree but a push sends HEAD, so they must match
    dirty = uncommitted(root, files)
    failures = [f"## uncommitted edits to pushed files\n{chr(10).join(dirty)}"] if dirty else []
    failures += [
        f"## suppression or skip added\n{hit}" for hit in suppression_findings(root, files)
    ]
    gates = select_gates(
        files,
        bool(shutil.which("uv")),
        bool(shutil.which("pnpm")) and (root / "frontend/node_modules").is_dir(),
        merge_base(root),
    )
    return failures + [msg for gate in gates if (msg := run_gate(root, gate))]


def evaluate(root: Path, session_id: str) -> tuple[int, str]:
    """return(tuple): (exit code, message) — 2 blocks the push and feeds the message back to the agent."""
    files = changed_files(root)
    if not files:
        return 0, ""
    state = load_state(session_id)
    fp = fingerprint(root, files)
    if state.get("passed") == fp:
        return 0, ""
    failures = _failures(root, files)
    if not failures:
        save_state(session_id, {"passed": fp, "rounds": 0})
        return 0, ""
    rounds = int(state.get("rounds", 0)) + 1
    save_state(session_id, {"passed": state.get("passed"), "rounds": rounds})
    if rounds > MAX_ROUNDS:
        message = (
            f"fast gates still failing after {MAX_ROUNDS} fix rounds; pushing for a human to look"
        )
        return 0, json.dumps({"systemMessage": message})
    header = (
        f"Push blocked: fast gates failed on this branch (fix round {rounds}/{MAX_ROUNDS}). "
        "Fix the cause, commit, and push again; do not suppress or skip."
    )
    return 2, "\n\n".join([header, *failures])


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    where = push_dir(command, Path(event.get("cwd") or "."))
    root = repo_root(where) if where else None
    if root is None:
        return 0
    code, message = evaluate(root, str(event.get("session_id", "default")))
    if message:
        print(message, file=sys.stderr if code == 2 else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
