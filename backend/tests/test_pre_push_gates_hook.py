import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "pre-push-gates.py"


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=root, check=True
    )


def _commit(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    _git(root, "add", *files)
    _git(root, "commit", "-qm", "change")


@pytest.fixture
def hook(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("pre_push_gates", HOOK_PATH)
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
    _git(root, "init", "-q", "-b", "main")
    _commit(root, {"README.md": "x\n"})
    _git(root, "checkout", "-qb", "feature")
    return root


@pytest.mark.unit
@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("git push", "."),
        ("git push -u origin feat-x", "."),
        ("git commit -qm 'x' && git push", "."),
        ("cd sub && git push", "sub"),
        ('cd "my dir" && git push', "my dir"),
        ("git -C sub push", "sub"),
        ("gh pr create --draft --base main", "."),
        ("git status", None),
        ("git pushy", None),
        ("git push origin --delete old-branch", None),
    ],
)
def test_push_dir(hook, tmp_path, command, expected):
    result = hook.push_dir(command, tmp_path)
    assert result == (None if expected is None else (tmp_path / expected).resolve())


@pytest.mark.unit
def test_select_gates_by_changed_area(hook):
    files = [
        "backend/community/views.py",
        "frontend/src/App.tsx",
        "frontend/visual/login.spec.ts",
        "docs/x.md",
    ]
    gates = hook.select_gates(files, have_uv=True, have_pnpm=True, base="abc123")
    names = [g.name for g in gates]
    assert names[:4] == ["ruff check", "ruff format", "ty", "affected pytest"]
    assert dict(gates[3].env) == {"TEST_BASE": "abc123"}
    assert "vitest related" in names
    oxlint = next(g for g in gates if g.name == "oxlint")
    assert oxlint.cmd[-1] == "src/App.tsx"
    assert "visual/login.spec.ts" not in oxlint.cmd


@pytest.mark.unit
def test_select_gates_skips_missing_tools(hook):
    files = ["backend/a.py", "frontend/src/a.ts"]
    assert hook.select_gates(files, have_uv=False, have_pnpm=False) == []


@pytest.mark.unit
def test_only_committed_changes_are_checked(hook, repo):
    assert hook.evaluate(repo, "s1") == (0, "")
    (repo / "scratch.py").write_text("x = 1\n")
    assert hook.changed_files(repo) == []
    _commit(repo, {"backend/a.py": "x = 1\n"})
    assert hook.changed_files(repo) == ["backend/a.py"]


@pytest.mark.unit
def test_uncommitted_edits_to_pushed_files_block(hook, repo, monkeypatch):
    _commit(repo, {"backend/a.py": "x = 1\n"})
    (repo / "backend" / "a.py").write_text("x = 2\n")
    monkeypatch.setattr(hook.shutil, "which", lambda name: None)
    code, message = hook.evaluate(repo, "s1")
    assert code == 2
    assert "## uncommitted edits to pushed files\nbackend/a.py" in message


@pytest.mark.unit
def test_failure_blocks_then_caps_after_three_rounds(hook, repo, monkeypatch):
    _commit(repo, {"backend/a.py": "x = 1\n"})
    monkeypatch.setattr(hook, "run_gate", lambda root, gate: f"## {gate.name} failed")
    monkeypatch.setattr(hook.shutil, "which", lambda name: "/bin/" + name)
    for round_no in (1, 2, 3):
        code, message = hook.evaluate(repo, "s1")
        assert code == 2
        assert f"fix round {round_no}/3" in message
        assert "## ruff check failed" in message
    code, message = hook.evaluate(repo, "s1")
    assert code == 0
    assert "for a human to look" in json.loads(message)["systemMessage"]


@pytest.mark.unit
def test_passing_run_is_cached_until_files_change(hook, repo, monkeypatch):
    _commit(repo, {"backend/a.py": "x = 1\n"})
    calls = []
    monkeypatch.setattr(hook, "run_gate", lambda root, gate: calls.append(gate.name))
    monkeypatch.setattr(hook.shutil, "which", lambda name: "/bin/" + name)
    assert hook.evaluate(repo, "s1") == (0, "")
    first = len(calls)
    assert hook.evaluate(repo, "s1") == (0, "")
    assert len(calls) == first
    _commit(repo, {"backend/a.py": "x = 2\n"})
    hook.evaluate(repo, "s1")
    assert len(calls) == 2 * first


@pytest.mark.unit
def test_added_suppression_blocks_push(hook, repo, monkeypatch):
    real = HOOK_PATH.parents[2] / "scripts" / "check_anti_tampering.py"
    banned = "@ts-" + "ignore"
    _commit(
        repo,
        {
            "scripts/check_anti_tampering.py": real.read_text(),
            "notes.ts": f"// {banned}\nconst a = 1;\n",
        },
    )
    monkeypatch.setattr(hook.shutil, "which", lambda name: None)
    code, message = hook.evaluate(repo, "s2")
    assert code == 2
    assert f"{banned} suppression" in message


def _stdin(monkeypatch, event: dict) -> None:
    payload = json.dumps(event)
    monkeypatch.setattr(sys, "stdin", type("S", (), {"read": lambda self: payload})())


@pytest.mark.unit
def test_main_ignores_non_push_commands(hook, repo, monkeypatch):
    monkeypatch.setattr(hook, "evaluate", lambda root, sid: pytest.fail("should not run"))
    _stdin(monkeypatch, {"cwd": str(repo), "tool_input": {"command": "git status"}})
    assert hook.main() == 0


@pytest.mark.unit
def test_main_gates_a_push_and_reports(hook, repo, monkeypatch, capsys):
    monkeypatch.setattr(hook, "evaluate", lambda root, sid: (2, f"blocked {root.name}"))
    _stdin(monkeypatch, {"cwd": str(repo), "tool_input": {"command": "git push -u origin feature"}})
    assert hook.main() == 2
    assert "blocked repo" in capsys.readouterr().err
