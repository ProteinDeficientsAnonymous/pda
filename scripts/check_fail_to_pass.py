#!/usr/bin/env python3
"""For a fix: run the PR's changed backend tests against the base code; they must fail there."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTEST_NO_TESTS_COLLECTED = 5


def changed_backend(base: str) -> tuple[list[str], list[str]]:
    """return(tuple): (changed test files, changed source files), repo-relative."""
    out = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=AM", f"{base}...HEAD", "--", "backend/"],
        cwd=REPO_ROOT,
        text=True,
    )
    files = [f for f in out.splitlines() if f.endswith(".py")]
    tests = [f for f in files if "/tests/" in f]
    return tests, [f for f in files if f not in tests]


def python_cmd() -> list[str]:
    venv_python = REPO_ROOT / ".venv" / "bin" / "python"
    return [str(venv_python)] if venv_python.exists() else ["uv", "run", "python"]


def run_on_base(base: str, tests: list[str]) -> int:
    parent = Path(tempfile.mkdtemp(prefix="fail-to-pass-"))
    subprocess.run(
        ["git", "worktree", "add", "--detach", "-q", str(parent), base], cwd=REPO_ROOT, check=True
    )
    try:
        for rel in tests:
            (parent / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / rel, parent / rel)
        targets = [t.removeprefix("backend/") for t in tests if Path(t).name.startswith("test_")]
        cmd = [
            *python_cmd(),
            "-m",
            "pytest",
            "-q",
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
            "--create-db",
            *targets,
        ]
        return subprocess.run(cmd, cwd=parent / "backend", check=False).returncode
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(parent)], cwd=REPO_ROOT, check=False
        )


def verdict(tests: list[str], sources: list[str], base_exit: int | None) -> str | None:
    """return(str | None): the problem to report, or None when the tests prove the fix."""
    if not sources:
        return None
    if not tests:
        return "fix changes backend code but adds or changes no backend test"
    if base_exit == PYTEST_NO_TESTS_COLLECTED:
        return "no tests collected from the changed test files"
    if base_exit == 0:
        return "changed tests already pass on the base code, so they do not prove the fix"
    return None


def _emit(problem: str | None, enforce: bool, ran: bool) -> None:
    if problem:
        text = f"Fail-to-pass: {problem}"
    elif ran:
        text = "Fail-to-pass: changed tests fail on the base code, as expected."
    else:
        text = "Fail-to-pass: no backend source change to prove."
    if problem and os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::{'error' if enforce else 'warning'}::{text}")
    else:
        print(text)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### {text}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.environ.get("DIFF_COVER_BASE", "origin/main"))
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args(argv)
    tests, sources = changed_backend(args.base)
    base_exit = run_on_base(args.base, tests) if tests and sources else None
    problem = verdict(tests, sources, base_exit)
    _emit(problem, args.enforce, ran=base_exit is not None)
    return 1 if problem and args.enforce else 0


if __name__ == "__main__":
    sys.exit(main())
