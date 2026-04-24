#!/usr/bin/env python3
"""PreToolUse hook: block new legacy error patterns in backend code.

We've migrated the codebase to structured validation errors: routes raise
``ValidationException`` (via ``raise_validation(Code.X.Y)``) and a global
handler reshapes to ``{ detail: [{code, field, params?}] }``. This hook
prevents regression.

Rules enforced:
  1. No new ``ErrorOut(detail="...")`` in backend/ (except tests, migrations,
     and files that still have legacy instances pending migration).
  2. No new ``raise ValueError("...")`` inside Pydantic schema files
     (``_*_schemas.py``). Schema validators should raise
     ``ValidationException`` or call ``raise_validation(Code.X.Y)``.

Exempt paths:
  - ``backend/tests/``
  - ``**/migrations/``
  - Any file whose current HEAD version already contains a forbidden pattern
    (meaning migration is still in progress for that file — allow edits
    while the count is non-increasing).

Exit codes:
  0 = allow the edit
  2 = block the edit (stderr message surfaces back to Claude)
"""

import json
import re
import subprocess
import sys
from pathlib import Path


# Patterns we don't want reintroduced.
ERROR_OUT_PATTERN = re.compile(r"ErrorOut\(detail=")
VALUE_ERROR_IN_SCHEMA_PATTERN = re.compile(r"\braise\s+ValueError\s*\(")

# Paths that may legitimately contain legacy patterns.
EXEMPT_PATH_FRAGMENTS = ("/tests/", "/migrations/", "/.claude/hooks/")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Can't parse input — don't block, but also don't crash.
        return 0

    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Edit", "Write", "MultiEdit"):
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "")
    if not file_path or not file_path.endswith(".py"):
        return 0
    if any(frag in file_path for frag in EXEMPT_PATH_FRAGMENTS):
        return 0
    if "/backend/" not in file_path:
        return 0

    # The content that will be in the file after the edit. For Write, that's
    # `content`. For Edit, that's the post-edit state we need to reconstruct
    # from `old_string` → `new_string` against the current file.
    new_content = _resolve_post_edit_content(tool_name, tool_input, file_path)
    if new_content is None:
        # Couldn't figure out post-state — don't block.
        return 0

    # If the current HEAD version of the file already contains legacy
    # patterns, migration is still in progress — allow edits. The hook only
    # guards files that are currently clean.
    head_content = _read_head_content(file_path)
    if head_content is None:
        head_content = ""

    violations: list[str] = []

    # ErrorOut rule applies to all backend files.
    new_error_outs = len(ERROR_OUT_PATTERN.findall(new_content))
    head_error_outs = len(ERROR_OUT_PATTERN.findall(head_content))
    if head_error_outs == 0 and new_error_outs > 0:
        violations.append(
            f"  - adds `ErrorOut(detail=...)` — use `raise_validation(Code.X.Y, status_code=...)` "
            f"from `community._validation` instead."
        )
    elif new_error_outs > head_error_outs:
        violations.append(
            f"  - adds a new `ErrorOut(detail=...)` call (was {head_error_outs}, now {new_error_outs}). "
            f"migration is in progress — don't add new instances. "
            f"use `raise_validation(Code.X.Y, status_code=...)` instead."
        )

    # ValueError-in-schema rule applies only to *_schemas.py files.
    if "_schemas.py" in Path(file_path).name:
        new_value_errors = len(VALUE_ERROR_IN_SCHEMA_PATTERN.findall(new_content))
        head_value_errors = len(VALUE_ERROR_IN_SCHEMA_PATTERN.findall(head_content))
        if new_value_errors > head_value_errors:
            violations.append(
                f"  - adds `raise ValueError(...)` in a Pydantic schema file. "
                f"use `raise_validation(Code.X.Y, field=\"...\")` so the error carries a "
                f"machine-readable code for the frontend."
            )

    if not violations:
        return 0

    sys.stderr.write(
        "\n".join(
            [
                f"❌ validation-error-pattern hook blocked edit to {file_path}:",
                *violations,
                "",
                "see `backend/community/_validation.py` for the `Code` catalog and "
                "`raise_validation` helper. if you're intentionally leaving a legacy "
                "string (e.g. for a success response), rename `ErrorOut` locally to avoid "
                "the match, or exempt this file via the hook.",
            ]
        )
        + "\n"
    )
    return 2


def _resolve_post_edit_content(
    tool_name: str, tool_input: dict, file_path: str
) -> str | None:
    """Return the file content as it would be after the tool applies."""
    if tool_name == "Write":
        return tool_input.get("content", "")

    # Edit / MultiEdit: need to apply the swap(s) against the on-disk file.
    try:
        current = Path(file_path).read_text()
    except (OSError, UnicodeDecodeError):
        return None

    if tool_name == "Edit":
        old = tool_input.get("old_string", "")
        new = tool_input.get("new_string", "")
        replace_all = tool_input.get("replace_all", False)
        if not old:
            return current
        if replace_all:
            return current.replace(old, new)
        return current.replace(old, new, 1)

    if tool_name == "MultiEdit":
        edits = tool_input.get("edits", []) or []
        result = current
        for edit in edits:
            old = edit.get("old_string", "")
            new = edit.get("new_string", "")
            replace_all = edit.get("replace_all", False)
            if not old:
                continue
            if replace_all:
                result = result.replace(old, new)
            else:
                result = result.replace(old, new, 1)
        return result

    return None


def _read_head_content(file_path: str) -> str | None:
    """Return the file's HEAD content from git, or None if not tracked."""
    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:./{_relpath(file_path)}"],
            capture_output=True,
            text=True,
            cwd=_repo_root(file_path),
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _repo_root(file_path: str) -> str:
    p = Path(file_path).resolve()
    while p != p.parent:
        if (p / ".git").exists():
            return str(p)
        p = p.parent
    return str(Path(file_path).parent)


def _relpath(file_path: str) -> str:
    root = Path(_repo_root(file_path))
    try:
        return str(Path(file_path).resolve().relative_to(root))
    except ValueError:
        return file_path


if __name__ == "__main__":
    sys.exit(main())
