#!/usr/bin/env python3
"""Fail when the tree contains lint/type suppressions or unconditional skipped tests."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        "coverage",
        "playwright-report",
        "test-results",
        "migrations",
    }
)

SCAN_ROOTS = ("backend", "frontend", "scripts")
SCAN_SUFFIXES = frozenset({".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"})

EXEMPT_PATHS = frozenset(
    {
        "scripts/check_anti_tampering.py",
        "backend/tests/test_check_anti_tampering.py",
    }
)

PATTERNS: tuple[tuple[str, str], ...] = (
    ("noqa suppression", r"#\s*noqa\b"),
    ("type: ignore suppression", r"#\s*type:\s*ignore\b"),
    ("pyright: ignore suppression", r"#\s*pyright:\s*ignore\b"),
    ("nosec suppression", r"#\s*nosec\b"),
    ("oxlint-disable suppression", r"oxlint-disable"),
    ("eslint-disable suppression", r"eslint-disable"),
    ("@ts-expect-error suppression", r"@ts-expect-error"),
    ("@ts-ignore suppression", r"@ts-ignore"),
    ("@ts-nocheck suppression", r"@ts-nocheck"),
    # skipif is allowed; only unconditional skips are banned.
    ("skipped pytest test", r"@pytest\.mark\.skip(?:\b|\()|pytest\.skip\("),
    ("skipped unittest test", r"@unittest\.skip\b"),
    ("skipped JS/TS test", r"\b(?:it|test|describe)\.skip\("),
)


def _compile_patterns():
    import re

    return tuple((label, re.compile(pattern)) for label, pattern in PATTERNS)


COMPILED = _compile_patterns()


def scan_text(rel_path: str, text: str) -> list[str]:
    if rel_path in EXEMPT_PATHS:
        return []
    findings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for label, pattern in COMPILED:
            if pattern.search(line):
                findings.append(f"{rel_path}:{lineno}: {label} -> {line.strip()}")
    return findings


def _iter_files(root: Path):
    for base_name in SCAN_ROOTS:
        base = root / base_name
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                continue
            if SKIP_DIR_NAMES.intersection(path.relative_to(root).parts):
                continue
            yield path


def scan_tree(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(_iter_files(root)):
        rel = str(path.relative_to(root))
        findings.extend(scan_text(rel, path.read_text(encoding="utf-8")))
    return findings


def main() -> int:
    findings = scan_tree(REPO_ROOT)
    for item in findings:
        print(item)
    if findings:
        print("Fix the underlying issue instead of suppressing checks or skipping tests.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
