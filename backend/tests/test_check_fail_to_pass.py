import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_fail_to_pass.py"


@pytest.fixture
def mod(monkeypatch):
    spec = importlib.util.spec_from_file_location("check_fail_to_pass", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    return module


@pytest.mark.unit
def test_changed_backend_splits_tests_from_sources(mod, monkeypatch):
    out = "backend/tests/test_a.py\nbackend/community/views.py\nbackend/README.md\n"
    monkeypatch.setattr(mod.subprocess, "check_output", lambda *a, **k: out)
    assert mod.changed_backend("origin/main") == (
        ["backend/tests/test_a.py"],
        ["backend/community/views.py"],
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("tests", "sources", "base_exit", "expected"),
    [
        ([], [], None, None),
        (["backend/tests/test_a.py"], [], None, None),
        ([], ["backend/a.py"], None, "adds or changes no backend test"),
        (["backend/tests/test_a.py"], ["backend/a.py"], 0, "already pass on the base code"),
        (["backend/tests/test_a.py"], ["backend/a.py"], 5, "no tests collected"),
        (["backend/tests/test_a.py"], ["backend/a.py"], 1, None),
        (["backend/tests/test_a.py"], ["backend/a.py"], 2, None),
    ],
)
def test_verdict(mod, tests, sources, base_exit, expected):
    problem = mod.verdict(tests, sources, base_exit)
    if expected is None:
        assert problem is None
    else:
        assert problem is not None and expected in problem


@pytest.mark.unit
def test_main_skips_base_run_without_sources(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "changed_backend", lambda base: (["backend/tests/test_a.py"], []))
    monkeypatch.setattr(mod, "run_on_base", lambda base, tests: pytest.fail("should not run"))
    assert mod.main(["--enforce"]) == 0
    assert "no backend source change to prove" in capsys.readouterr().out


@pytest.mark.unit
def test_main_warns_then_enforces_when_tests_pass_on_base(mod, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        mod, "changed_backend", lambda base: (["backend/tests/test_a.py"], ["backend/a.py"])
    )
    monkeypatch.setattr(mod, "run_on_base", lambda base, tests: 0)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert mod.main([]) == 0
    assert mod.main(["--enforce"]) == 1
    out = capsys.readouterr().out
    assert "::warning::Fail-to-pass: changed tests already pass" in out
    assert "::error::" in out
    assert "already pass on the base code" in summary.read_text()


@pytest.mark.unit
def test_run_on_base_copies_new_tests_into_a_base_worktree(mod, monkeypatch):
    commands: list[list[str]] = []

    class Done:
        returncode = 1

    def fake_run(cmd, cwd=None, check=False):
        commands.append(cmd)
        if cmd[:3] == ["git", "worktree", "add"]:
            (Path(cmd[-2]) / "backend" / "tests").mkdir(parents=True)
        if "pytest" in cmd:
            assert (Path(cwd) / "tests" / "test_check_fail_to_pass.py").is_file()
        return Done()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    assert mod.run_on_base("abc123", ["backend/tests/test_check_fail_to_pass.py"]) == 1
    pytest_cmd = next(c for c in commands if "pytest" in c)
    assert pytest_cmd[-1] == "tests/test_check_fail_to_pass.py"
    assert commands[-1][:3] == ["git", "worktree", "remove"]


@pytest.mark.unit
def test_python_cmd_prefers_repo_venv(mod, monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    assert mod.python_cmd() == ["uv", "run", "python"]
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("")
    assert mod.python_cmd() == [str(tmp_path / ".venv" / "bin" / "python")]
