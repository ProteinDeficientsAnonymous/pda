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


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


shell_parse = _load_module("shell_parse", Path(__file__).with_name("shell_parse.py"))


def is_gate_path(root: Path, rel: str) -> bool:
    script = root / "scripts" / "check_diff_tampering.py"
    if not script.is_file():
        return False
    return _load_module("check_diff_tampering", script).is_gate_path(rel)


def _gate_reason(path: Path) -> str | None:
    root = repo_root_of(path)
    if root is None:
        return None
    try:
        rel = path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return None
    try:
        gated = is_gate_path(root, rel)
    except Exception as exc:  # a broken checker must not switch the guard off
        return f"the gate-path checker failed to load ({exc!r}), so {rel} is treated as gate config"
    if not gated:
        return None
    return f"{rel} is gate config (CI, hooks, checkers). Agents may change it only with the human's explicit OK."


def _targets(event: dict) -> list[Path]:
    tool_input = event.get("tool_input") or {}
    if command := tool_input.get("command"):
        return shell_parse.write_targets(command, Path(event.get("cwd") or "."))
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    return [Path(raw).resolve()] if raw else []


def decision(event: dict) -> dict | None:
    reason = next((r for path in _targets(event) if (r := _gate_reason(path))), None)
    if reason is None:
        return None
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
