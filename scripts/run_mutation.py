#!/usr/bin/env python3
"""Run diff-scoped mutation testing on changed backend Python files."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _changed_backend_files(base: str) -> list[str]:
    out = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=AM", f"{base}...HEAD", "--", "backend/"],
        cwd=REPO_ROOT,
        text=True,
    )
    files: list[str] = []
    for raw in out.splitlines():
        if not raw.endswith(".py"):
            continue
        if "/tests/" in raw or "/migrations/" in raw:
            continue
        files.append(raw.removeprefix("backend/"))
    return files


def main() -> int:
    base = os.environ.get("DIFF_COVER_BASE", "origin/main")
    targets = sys.argv[1:] if len(sys.argv) > 1 else _changed_backend_files(base)
    if not targets:
        print("No changed backend domain files to mutate.")
        return 0
    print("Mutating:", ", ".join(targets))
    cmd = [
        "uv",
        "run",
        "--with",
        "mutmut",
        "mutmut",
        "run",
        "--paths-to-mutate",
        ",".join(targets),
    ]
    return subprocess.call(cmd, cwd=REPO_ROOT / "backend")


if __name__ == "__main__":
    raise SystemExit(main())
