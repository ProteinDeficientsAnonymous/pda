#!/usr/bin/env python3
"""Run diff-scoped mutation testing on changed backend Python files; report survivors."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"
# mutmut 3 dropped --paths-to-mutate/--runner and copies the tree into mutants/, which Django settings don't survive
MUTMUT = ["uv", "run", "--with", "mutmut==2.5.1", "mutmut"]
MAX_SHOWN = 20


def changed_backend_files(base: str) -> list[str]:
    out = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=AM", f"{base}...HEAD", "--", "backend/"],
        cwd=REPO_ROOT,
        text=True,
    )
    return [
        raw.removeprefix("backend/")
        for raw in out.splitlines()
        if raw.endswith(".py") and "/tests/" not in raw and "/migrations/" not in raw
    ]


def affected_tests(base: str) -> list[str]:
    out = subprocess.check_output(
        [sys.executable, str(REPO_ROOT / "scripts" / "list_affected_tests.py"), "--base", base],
        cwd=REPO_ROOT,
        text=True,
    )
    paths = [line for line in out.splitlines() if line.strip()]
    return ["tests/"] if not paths or "__FULL__" in paths else paths


def survivor_ids() -> list[str]:
    return _mutmut("result-ids", "survived").stdout.split()


def _mutmut(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*MUTMUT, *args], cwd=BACKEND, capture_output=True, text=True, check=False
    )


def report(survivors: list[str]) -> str:
    lines = [f"### Mutation testing: {len(survivors)} surviving mutant(s)", ""]
    for mutant in survivors[:MAX_SHOWN]:
        lines += ["```diff", _mutmut("show", mutant).stdout.strip(), "```"]
    if len(survivors) > MAX_SHOWN:
        lines.append(f"…and {len(survivors) - MAX_SHOWN} more (`mutmut results`).")
    lines.append(
        "Each survivor is a change to the code that no test noticed: add or tighten a test."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "paths", nargs="*", help="backend-relative files to mutate (default: changed files)"
    )
    parser.add_argument("--base", default=os.environ.get("DIFF_COVER_BASE", "origin/main"))
    parser.add_argument(
        "--tests", nargs="+", help="backend-relative pytest paths (default: affected by the diff)"
    )
    parser.add_argument(
        "--enforce", action="store_true", help="exit non-zero when any mutant survives"
    )
    args = parser.parse_args(argv)
    targets = args.paths or changed_backend_files(args.base)
    if not targets:
        print("No changed backend domain files to mutate.")
        return 0
    tests = args.tests or affected_tests(args.base)
    print("Mutating:", ", ".join(targets), "| tests:", " ".join(tests), flush=True)
    # results come from the cache, so a stale one would report another run's survivors
    (BACKEND / ".mutmut-cache").unlink(missing_ok=True)
    runner = "python -m pytest -x -q -o addopts= -p no:cacheprovider --reuse-db " + " ".join(tests)
    subprocess.run(
        [
            *MUTMUT,
            "run",
            "--paths-to-mutate",
            ",".join(targets),
            "--tests-dir",
            "tests",
            "--runner",
            runner,
        ],
        cwd=BACKEND,
        check=False,
    )
    survivors = survivor_ids()
    text = report(survivors) if survivors else "### Mutation testing: no surviving mutants"
    print(text)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 1 if survivors and args.enforce else 0


if __name__ == "__main__":
    sys.exit(main())
