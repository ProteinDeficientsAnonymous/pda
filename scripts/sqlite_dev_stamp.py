#!/usr/bin/env python3
"""Fingerprint + stamp cache for per-worktree SQLite dev.db init."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED_FILES = (
    "backend/community/management/commands/seed.py",
    "backend/community/management/commands/_seed_data.py",
)


def stamp_path(db_path: Path) -> Path:
    return db_path.with_name(f"{db_path.name}.stamp")


def fingerprint(root: Path = REPO_ROOT) -> str:
    hasher = hashlib.sha256()
    paths: list[Path] = []
    for migrations_dir in sorted((root / "backend").glob("*/migrations")):
        paths.extend(sorted(migrations_dir.glob("*.py")))
    for rel in SEED_FILES:
        paths.append(root / rel)
    for path in paths:
        rel = path.relative_to(root).as_posix().encode()
        hasher.update(rel)
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def is_current(db_path: Path, root: Path = REPO_ROOT) -> bool:
    db_path = db_path.resolve()
    stamp = stamp_path(db_path)
    if not db_path.is_file() or not stamp.is_file():
        return False
    return stamp.read_text().strip() == fingerprint(root)


def write_stamp(db_path: Path, root: Path = REPO_ROOT) -> None:
    db_path = db_path.resolve()
    stamp_path(db_path).write_text(f"{fingerprint(root)}\n")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2 or args[0] not in {"check", "write"}:
        print("usage: sqlite_dev_stamp.py {check|write} <dev.db-path>", file=sys.stderr)
        return 2
    db_path = Path(args[1])
    if args[0] == "check":
        return 0 if is_current(db_path) else 1
    write_stamp(db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
