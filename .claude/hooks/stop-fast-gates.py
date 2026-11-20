#!/usr/bin/env python3
"""Stop hook: block the agent from stopping while fast gates fail on its changed files."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

MAX_ROUNDS = 3
OUTPUT_TAIL_LINES = 40
STATE_DIR = Path(tempfile.gettempdir()) / "pda-stop-gate"
BASE_REFS = ("origin/main", "main")
CODE_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")


@dataclass(frozen=True)
class Gate:
    name: str
    cmd: list[str]
    cwd: str


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def changed_files(root: Path) -> list[str]:
    merge_base = next(
        (mb for ref in BASE_REFS if (mb := git(root, "merge-base", "HEAD", ref))), "HEAD"
    )
    tracked = git(root, "diff", "--name-only", merge_base).splitlines()
    untracked = git(root, "ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({p for p in tracked + untracked if p and (root / p).is_file()})


def fingerprint(root: Path, files: list[str]) -> str:
    digest = hashlib.sha256()
    for rel in files:
        digest.update(rel.encode())
        digest.update((root / rel).read_bytes())
    return digest.hexdigest()


def select_gates(files: list[str], have_uv: bool, have_pnpm: bool) -> list[Gate]:
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
            Gate("affected pytest", ["make", "-s", "agent-test-since"], "."),
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
        gate.cmd, cwd=root / gate.cwd, capture_output=True, text=True, check=False
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


def repo_root(event: dict) -> Path | None:
    top = git(Path(event.get("cwd") or "."), "rev-parse", "--show-toplevel")
    return Path(top) if top else None


def evaluate(root: Path, session_id: str) -> tuple[int, str]:
    """return(tuple): (exit code, message) — 2 blocks the stop and feeds the message back to the agent."""
    files = changed_files(root)
    if not files:
        return 0, ""
    state = load_state(session_id)
    fp = fingerprint(root, files)
    if state.get("passed") == fp:
        return 0, ""
    failures = [f"## suppression or skip added\n{hit}" for hit in suppression_findings(root, files)]
    gates = select_gates(
        files,
        bool(shutil.which("uv")),
        bool(shutil.which("pnpm")) and (root / "frontend/node_modules").is_dir(),
    )
    failures += [msg for gate in gates if (msg := run_gate(root, gate))]
    if not failures:
        save_state(session_id, {"passed": fp, "rounds": 0})
        return 0, ""
    rounds = int(state.get("rounds", 0)) + 1
    save_state(session_id, {"passed": state.get("passed"), "rounds": rounds})
    if rounds > MAX_ROUNDS:
        return 0, json.dumps(
            {
                "systemMessage": f"fast gates still failing after {MAX_ROUNDS} fix rounds — needs a human"
            }
        )
    header = f"Fast gates failed on your changed files (fix round {rounds}/{MAX_ROUNDS}). Fix the cause; do not suppress or skip."
    return 2, "\n\n".join([header, *failures])


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    root = repo_root(event)
    if root is None:
        return 0
    code, message = evaluate(root, str(event.get("session_id", "default")))
    if message:
        print(message, file=sys.stderr if code == 2 else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
