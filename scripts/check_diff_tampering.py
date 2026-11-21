#!/usr/bin/env python3
"""Flag diffs that weaken tests or touch gate config; warns by default, fails with --enforce."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

GATE_PATH_PREFIXES = (
    ".github/",
    ".claude/hooks/",
    "scripts/check_",
    "scripts/run_mutation.py",
    "scripts/list_affected_tests.py",
    "frontend/tsconfig",
)
GATE_PATHS = frozenset(
    {
        "Makefile",
        "pyproject.toml",
        ".claude/settings.json",
        ".gitleaks.toml",
        "frontend/.oxlintrc.json",
        "frontend/.oxfmtrc.json",
        "frontend/package.json",
        "frontend/vitest.config.ts",
        "frontend/playwright.config.ts",
        "frontend/playwright.visual.config.ts",
    }
)

TEST_FILE = re.compile(
    r"^backend/(?:.+/)?tests/(?:.+/)?test_[^/]+\.py$"
    r"|^frontend/(?:e2e|visual)/.+\.ts$"
    r"|^frontend/.+\.test\.tsx?$"
)
TEST_DEF = re.compile(r"^\s*(?:async\s+)?def\s+test_\w*|^\s*(?:it|test)(?:\.each\(.*?\))?\(")
ASSERTION = re.compile(r"\bassert\b|\bexpect(?:\.\w+)?\(|\bself\.assert\w+\(|\bpytest\.raises\(")
TRIVIAL_ASSERTION = re.compile(
    r"^\s*assert\s+(?:True|1|not\s+False)\s*(?:,.*)?(?:#.*)?$"
    r"|^\s*assert\s+(?P<same>[\w.]+|'[^']*'|\"[^\"]*\")\s*==\s*(?P=same)\s*(?:,.*)?(?:#.*)?$"
    r"|^\s*assert\s+.+\s+or\s+True\s*(?:,.*)?(?:#.*)?$"
    r"|expect\((?:true|1)\)\.(?:toBe\((?:true|1)\)|toBeTruthy\(\))"
    r"|expect\((?P<lit>\d+|true|false|'[^']*'|\"[^\"]*\")\)\.(?:toBe|toEqual)\((?P=lit)\)"
)


@dataclass
class FileDelta:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)


def is_gate_path(path: str) -> bool:
    return path in GATE_PATHS or path.startswith(GATE_PATH_PREFIXES)


def parse_diff(diff_text: str) -> dict[str, FileDelta]:
    """param(str): unified diff with --no-renames. return(dict): path -> added/removed lines."""
    deltas: dict[str, FileDelta] = {}
    current: FileDelta | None = None
    in_header = False
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            current, in_header = None, True
        elif line.startswith("@@"):
            in_header = False
        elif in_header:
            if line.startswith(("--- a/", "+++ b/")):
                current = deltas.setdefault(line[6:], FileDelta())
        elif current is not None and line.startswith("+"):
            current.added.append(line[1:])
        elif current is not None and line.startswith("-"):
            current.removed.append(line[1:])
    return deltas


def _count(pattern: re.Pattern[str], lines: list[str]) -> int:
    return sum(1 for line in lines if pattern.search(line))


def _net_loss(pattern: re.Pattern[str], delta: FileDelta) -> int:
    return _count(pattern, delta.removed) - _count(pattern, delta.added)


def _test_file_findings(path: str, delta: FileDelta, net: dict[str, bool]) -> list[str]:
    findings: list[str] = []
    if net["tests"] and (lost := _net_loss(TEST_DEF, delta)) > 0:
        findings.append(f"{path}: {lost} test(s) removed")
    if net["asserts"] and (lost := _net_loss(ASSERTION, delta)) > 0:
        findings.append(f"{path}: net {lost} assertion(s) removed")
    trivial = [line.strip() for line in delta.added if TRIVIAL_ASSERTION.search(line)]
    findings.extend(f"{path}: trivially-true assertion added -> {line}" for line in trivial)
    return findings


def analyse(deltas: dict[str, FileDelta]) -> list[str]:
    test_paths = [path for path in sorted(deltas) if TEST_FILE.match(path)]
    # netted across the diff so moving or renaming tests between files isn't reported as loss
    net = {
        key: sum(_net_loss(pattern, deltas[p]) for p in test_paths) > 0
        for key, pattern in (("tests", TEST_DEF), ("asserts", ASSERTION))
    }
    findings: list[str] = []
    for path in sorted(deltas):
        if is_gate_path(path):
            findings.append(f"{path}: gate config changed — needs a human reviewer")
        if path in test_paths:
            findings.extend(_test_file_findings(path, deltas[path], net))
    return findings


def branch_diff(base: str) -> str:
    return subprocess.check_output(
        ["git", "diff", "--no-renames", "--unified=0", f"{base}...HEAD"],
        cwd=REPO_ROOT,
        text=True,
    )


def _report(findings: list[str], enforce: bool) -> None:
    level = "error" if enforce else "warning"
    in_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    for item in findings:
        path, _, message = item.partition(": ")
        print(f"::{level} file={path}::{message}" if in_ci else item)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary and findings:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("### Diff tampering check\n\n")
            fh.writelines(f"- `{item}`\n" for item in findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.environ.get("DIFF_COVER_BASE", "origin/main"))
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args(argv)
    try:
        diff = branch_diff(args.base)
    except subprocess.CalledProcessError:
        print(f"::notice::cannot diff against {args.base}; diff tampering check skipped")
        return 1 if args.enforce else 0
    findings = analyse(parse_diff(diff))
    _report(findings, args.enforce)
    if not findings:
        print("No weakened tests or gate-config changes.")
        return 0
    return 1 if args.enforce else 0


if __name__ == "__main__":
    sys.exit(main())
