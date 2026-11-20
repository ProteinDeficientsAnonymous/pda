#!/usr/bin/env python3
"""PreToolUse hook: require the human's approval before an agent edits gate config."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def repo_root_of(path: Path) -> Path | None:
    existing = next((p for p in [path, *path.parents] if p.is_dir()), None)
    if existing is None:
        return None
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=existing,
        capture_output=True,
        text=True,
        check=False,
    )
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def is_gate_path(root: Path, rel: str) -> bool:
    script = root / "scripts" / "check_diff_tampering.py"
    spec = importlib.util.spec_from_file_location("check_diff_tampering", script)
    if not script.is_file() or spec is None or spec.loader is None:
        return False
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod.is_gate_path(rel)


def decision(event: dict) -> dict | None:
    raw = (event.get("tool_input") or {}).get("file_path") or (event.get("tool_input") or {}).get(
        "notebook_path"
    )
    if not raw:
        return None
    path = Path(raw).resolve()
    root = repo_root_of(path)
    if root is None:
        return None
    try:
        rel = path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return None
    if not is_gate_path(root, rel):
        return None
    reason = f"{rel} is gate config (CI, hooks, checkers). Agents may change it only with the human's explicit OK."
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    result = decision(event)
    if result:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
