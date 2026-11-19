#!/usr/bin/env python3
"""Fail on newly added lint/type suppressions or skipped tests in a git diff."""

from __future__ import annotations

import os
import re
import subprocess
import sys

EXEMPT_PATHS = frozenset(
    {
        "scripts/check_anti_tampering.py",
        "backend/tests/test_check_anti_tampering.py",
    }
)

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("noqa suppression", re.compile(r"#\s*noqa\b")),
    ("type: ignore suppression", re.compile(r"#\s*type:\s*ignore\b")),
    ("pyright: ignore suppression", re.compile(r"#\s*pyright:\s*ignore\b")),
    ("nosec suppression", re.compile(r"#\s*nosec\b")),
    ("oxlint-disable suppression", re.compile(r"oxlint-disable")),
    ("eslint-disable suppression", re.compile(r"eslint-disable")),
    ("@ts-expect-error suppression", re.compile(r"@ts-expect-error")),
    ("@ts-ignore suppression", re.compile(r"@ts-ignore")),
    ("@ts-nocheck suppression", re.compile(r"@ts-nocheck")),
    ("skipped pytest test", re.compile(r"@pytest\.mark\.skip\b|pytest\.skip\(")),
    ("skipped unittest test", re.compile(r"@unittest\.skip\b")),
    ("skipped JS/TS test", re.compile(r"\b(?:it|test|describe)\.skip\(")),
)


def scan_diff(diff_text: str) -> list[str]:
    findings: list[str] = []
    current_file = ""
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if current_file in EXEMPT_PATHS:
            continue
        added = line[1:]
        for label, pattern in PATTERNS:
            if pattern.search(added):
                findings.append(f"{current_file}: {label} -> {added.strip()}")
    return findings


def _git_diff(base: str | None) -> str:
    cmd = ["git", "diff", "--unified=0"]
    if base:
        cmd.append(f"{base}...HEAD")
    return subprocess.check_output(cmd, text=True)


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ANTI_TAMPER_BASE")
    findings = scan_diff(_git_diff(base))
    for item in findings:
        print(item)
    if findings:
        print("Fix the underlying issue instead of suppressing checks or skipping tests.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
