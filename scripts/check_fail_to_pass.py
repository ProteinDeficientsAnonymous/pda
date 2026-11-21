#!/usr/bin/env python3
"""For a fix: run the PR's changed backend tests against the base code; they must fail there."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTEST_TESTS_FAILED = 1
PYTEST_COLLECTION_ERROR = 2
PYTEST_NO_TESTS_COLLECTED = 5
IMPORT_ERROR = re.compile(r"\b(?:ImportError|ModuleNotFoundError)\b")


@dataclass(frozen=True)
class BaseRun:
    exit_code: int
    failures: int = 0
    import_errors: int = 0


def changed_backend(base: str) -> tuple[list[str], list[str], list[str]]:
    """return(tuple): (changed test_*.py files, other changed files under tests/, changed source files)."""
    out = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=AM", f"{base}...HEAD", "--", "backend/"],
        cwd=REPO_ROOT,
        text=True,
    )
    files = [f for f in out.splitlines() if f.endswith(".py")]
    in_tests = [f for f in files if "/tests/" in f]
    tests = [f for f in in_tests if Path(f).name.startswith("test_")]
    support = [f for f in in_tests if f not in tests]
    sources = [f for f in files if f not in in_tests and "/migrations/" not in f]
    return tests, support, sources


def python_cmd() -> list[str]:
    venv_python = REPO_ROOT / ".venv" / "bin" / "python"
    return [str(venv_python)] if venv_python.exists() else ["uv", "run", "python"]


def junit_counts(path: Path) -> tuple[int, int]:
    """return(tuple): (test cases that failed an assertion, cases that errored on an import)."""
    try:
        cases = ElementTree.parse(path).getroot().iter("testcase")
    except (OSError, ElementTree.ParseError):
        return 0, 0
    failures = import_errors = 0
    for case in cases:
        if case.find("failure") is not None:
            failures += 1
        elif (err := case.find("error")) is not None:
            import_errors += bool(IMPORT_ERROR.search(f"{err.get('message', '')} {err.text or ''}"))
    return failures, import_errors


def run_on_base(base: str, tests: list[str], support: list[str]) -> BaseRun | None:
    """return(BaseRun | None): the changed tests' result on the base code; None if it can't be checked out."""
    parent = Path(tempfile.mkdtemp(prefix="fail-to-pass-"))
    added = subprocess.run(
        ["git", "worktree", "add", "--detach", "-q", str(parent), base],
        cwd=REPO_ROOT,
        check=False,
    )
    if added.returncode != 0:
        shutil.rmtree(parent, ignore_errors=True)
        return None
    try:
        for rel in [*tests, *support]:
            (parent / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / rel, parent / rel)
        junit = parent / "fail-to-pass.xml"
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
            f"--junitxml={junit}",
            *(t.removeprefix("backend/") for t in tests),
        ]
        code = subprocess.run(cmd, cwd=parent / "backend", check=False).returncode
        return BaseRun(code, *junit_counts(junit))
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(parent)], cwd=REPO_ROOT, check=False
        )


def verdict(tests: list[str], sources: list[str], base: BaseRun | None) -> str | None:
    """return(str | None): the problem to report, or None when the tests prove the fix."""
    if not sources:
        return None
    if not tests:
        return "fix changes backend code but adds or changes no backend test_*.py file"
    if base is None:
        return "could not check out the base commit, so the fix was not checked"
    return _base_problem(base)


def _base_problem(base: BaseRun) -> str | None:
    if base.exit_code == PYTEST_NO_TESTS_COLLECTED:
        return "no tests collected from the changed test files"
    if base.exit_code == 0:
        return "changed tests already pass on the base code, so they do not prove the fix"
    if base.exit_code not in (PYTEST_TESTS_FAILED, PYTEST_COLLECTION_ERROR):
        return f"pytest could not run the changed tests on the base code (exit {base.exit_code})"
    if base.failures or base.import_errors:
        return None
    return "changed tests only error on the base code (setup, fixture or database), which does not prove the fix"


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
    tests, support, sources = changed_backend(args.base)
    base = run_on_base(args.base, tests, support) if tests and sources else None
    problem = verdict(tests, sources, base)
    _emit(problem, args.enforce, ran=base is not None)
    return 1 if problem and args.enforce else 0


if __name__ == "__main__":
    sys.exit(main())
