import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "stop-fast-gates.py"


@pytest.fixture
def hook(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("stop_fast_gates", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "STATE_DIR", tmp_path / "state")
    return mod


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    (root / "README.md").write_text("x\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
        cwd=root,
        check=True,
    )
    return root


@pytest.mark.unit
def test_select_gates_by_changed_area(hook):
    files = [
        "backend/community/views.py",
        "frontend/src/App.tsx",
        "frontend/visual/login.spec.ts",
        "docs/x.md",
    ]
    gates = hook.select_gates(files, have_uv=True, have_pnpm=True)
    names = [g.name for g in gates]
    assert names[:4] == ["ruff check", "ruff format", "ty", "affected pytest"]
    assert "vitest related" in names
    oxlint = next(g for g in gates if g.name == "oxlint")
    assert oxlint.cmd[-1] == "src/App.tsx"
    assert "visual/login.spec.ts" not in oxlint.cmd


@pytest.mark.unit
def test_select_gates_skips_missing_tools(hook):
    assert (
        hook.select_gates(["backend/a.py", "frontend/src/a.ts"], have_uv=False, have_pnpm=False)
        == []
    )


@pytest.mark.unit
def test_no_changes_allows_stop(hook, repo):
    assert hook.evaluate(repo, "s1") == (0, "")


@pytest.mark.unit
def test_failure_blocks_then_caps_after_three_rounds(hook, repo, monkeypatch):
    (repo / "backend").mkdir()
    (repo / "backend" / "a.py").write_text("x = 1\n")
    monkeypatch.setattr(hook, "run_gate", lambda root, gate: f"## {gate.name} failed")
    monkeypatch.setattr(hook.shutil, "which", lambda name: "/bin/" + name)
    for round_no in (1, 2, 3):
        code, message = hook.evaluate(repo, "s1")
        assert code == 2
        assert f"fix round {round_no}/3" in message
        assert "## ruff check failed" in message
    code, message = hook.evaluate(repo, "s1")
    assert code == 0
    assert "needs a human" in json.loads(message)["systemMessage"]


@pytest.mark.unit
def test_passing_run_is_cached_until_files_change(hook, repo, monkeypatch):
    (repo / "backend").mkdir()
    target = repo / "backend" / "a.py"
    target.write_text("x = 1\n")
    calls = []
    monkeypatch.setattr(hook, "run_gate", lambda root, gate: calls.append(gate.name))
    monkeypatch.setattr(hook.shutil, "which", lambda name: "/bin/" + name)
    assert hook.evaluate(repo, "s1") == (0, "")
    first = len(calls)
    assert hook.evaluate(repo, "s1") == (0, "")
    assert len(calls) == first
    target.write_text("x = 2\n")
    hook.evaluate(repo, "s1")
    assert len(calls) == 2 * first


@pytest.mark.unit
def test_added_suppression_blocks_stop(hook, repo, monkeypatch):
    scripts = repo / "scripts"
    scripts.mkdir()
    real = HOOK_PATH.parents[2] / "scripts" / "check_anti_tampering.py"
    (scripts / "check_anti_tampering.py").write_text(real.read_text())
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "s"],
        cwd=repo,
        check=True,
    )
    banned = "@ts-" + "ignore"
    (repo / "notes.ts").write_text(f"// {banned}\nconst a = 1;\n")
    monkeypatch.setattr(hook.shutil, "which", lambda name: None)
    code, message = hook.evaluate(repo, "s2")
    assert code == 2
    assert f"{banned} suppression" in message


@pytest.mark.unit
def test_main_reads_event_and_reports(hook, repo, monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "stdin", type("S", (), {"read": lambda self: json.dumps({"cwd": str(repo)})})()
    )
    assert hook.main() == 0
    monkeypatch.setattr(hook, "evaluate", lambda root, sid: (2, "blocked"))
    assert hook.main() == 2
    assert "blocked" in capsys.readouterr().err
