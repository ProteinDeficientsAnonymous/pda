import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
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
