import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests._paths import REPO_ROOT

HOOK_PATH = REPO_ROOT / ".claude" / "hooks" / "guard-gate-files.py"


@pytest.fixture
def hook():
    spec = importlib.util.spec_from_file_location("guard_gate_files", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _event(path: Path) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": str(path)}}


@pytest.mark.unit
@pytest.mark.parametrize(
    "rel", [".github/workflows/ci.yml", "Makefile", ".claude/hooks/new-hook.py"]
)
def test_gate_file_edit_asks_the_human(hook, rel):
    result = hook.decision(_event(REPO_ROOT / rel))
    assert result is not None
    out = result["hookSpecificOutput"]
    assert out["permissionDecision"] == "ask"
    assert rel in out["permissionDecisionReason"]


@pytest.mark.unit
@pytest.mark.parametrize("rel", ["backend/community/views.py", "frontend/src/App.tsx"])
def test_ordinary_edit_is_allowed(hook, rel):
    assert hook.decision(_event(REPO_ROOT / rel)) is None


@pytest.mark.unit
def test_paths_outside_a_repo_or_missing_are_allowed(hook, tmp_path):
    assert hook.decision(_event(tmp_path / "Makefile")) is None
    assert hook.decision({"tool_input": {}}) is None


@pytest.mark.unit
def test_main_prints_decision_json(hook, monkeypatch, capsys):
    payload = json.dumps(_event(REPO_ROOT / "Makefile"))
    monkeypatch.setattr(sys, "stdin", type("S", (), {"read": lambda self: payload})())
    assert hook.main() == 0
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecision"] == "ask"


def _bash(command: str, cwd: Path = REPO_ROOT) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}


@pytest.mark.unit
@pytest.mark.parametrize(
    "command",
    [
        "sed -i 's/a/b/' Makefile",
        "perl -pi -e 's/a/b/' Makefile",
        "echo x >> .github/workflows/ci.yml",
        "cat x | tee .claude/settings.json",
        "cd .github && rm workflows/ci.yml",
        "cp /tmp/x scripts/check_anti_tampering.py",
        "printf '' > pyproject.toml 2>/dev/null",
    ],
)
def test_bash_write_to_gate_file_asks_the_human(hook, command):
    result = hook.decision(_bash(command))
    assert result is not None
    assert result["hookSpecificOutput"]["permissionDecision"] == "ask"


@pytest.mark.unit
@pytest.mark.parametrize(
    "command",
    [
        "cat Makefile",
        "grep -n x .github/workflows/ci.yml",
        "echo x > backend/notes.txt",
        "git status 2>&1",
        "sed -n 1,5p Makefile",
    ],
)
def test_bash_reads_and_ordinary_writes_are_allowed(hook, command):
    assert hook.decision(_bash(command)) is None


@pytest.mark.unit
def test_broken_checker_asks_instead_of_failing_open(hook, monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "scripts" / "check_diff_tampering.py").write_text("def is_gate_path(:\n")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    result = hook.decision(_event(repo / "README.md"))
    assert result is not None
    reason = result["hookSpecificOutput"]["permissionDecisionReason"]
    assert "failed to load" in reason
