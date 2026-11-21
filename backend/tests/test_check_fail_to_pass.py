import importlib.util
import sys
from pathlib import Path

import pytest

from tests._paths import REPO_ROOT

SCRIPT_PATH = REPO_ROOT / "scripts" / "check_fail_to_pass.py"


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


T = ["backend/tests/test_a.py"]
S = ["backend/a.py"]


@pytest.mark.unit
def test_changed_backend_splits_tests_helpers_and_sources(mod, monkeypatch):
    out = (
        "backend/tests/users/test_a.py\nbackend/tests/_helpers.py\nbackend/tests/conftest.py\n"
        "backend/community/views.py\nbackend/community/migrations/0002_x.py\nbackend/README.md\n"
    )
    monkeypatch.setattr(mod.subprocess, "check_output", lambda *a, **k: out)
    assert mod.changed_backend("origin/main") == (
        ["backend/tests/users/test_a.py"],
        ["backend/tests/_helpers.py", "backend/tests/conftest.py"],
        ["backend/community/views.py"],
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("tests", "sources", "base", "expected"),
    [
        ([], [], None, None),
        (T, [], None, None),
        ([], S, None, "adds or changes no backend test_*.py file"),
        (T, S, None, "could not check out the base commit"),
        (T, S, (0, 0, 0), "already pass on the base code"),
        (T, S, (5, 0, 0), "no tests collected"),
        (T, S, (4, 0, 0), "could not run the changed tests on the base code (exit 4)"),
        (T, S, (1, 0, 0), "only error on the base code"),
        (T, S, (1, 1, 0), None),
        (T, S, (2, 0, 1), None),
    ],
)
def test_verdict(mod, tests, sources, base, expected):
    problem = mod.verdict(tests, sources, mod.BaseRun(*base) if base else None)
    if expected is None:
        assert problem is None
    else:
        assert problem is not None and expected in problem


@pytest.mark.unit
def test_junit_counts_assertion_failures_and_import_errors(mod, tmp_path):
    junit = tmp_path / "j.xml"
    junit.write_text(
        "<testsuites><testsuite>"
        '<testcase name="a"><failure message="assert 1 == 2"/></testcase>'
        '<testcase name="b"><error message="collection failure">ImportError: cannot import</error></testcase>'
        '<testcase name="c"><error message="OperationalError: db down"/></testcase>'
        '<testcase name="d"/>'
        "</testsuite></testsuites>"
    )
    assert mod.junit_counts(junit) == (1, 1)
    assert mod.junit_counts(tmp_path / "missing.xml") == (0, 0)


@pytest.mark.unit
def test_main_skips_base_run_without_sources(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "changed_backend", lambda base: (T, [], []))
    monkeypatch.setattr(mod, "run_on_base", lambda *a: pytest.fail("should not run"))
    assert mod.main(["--enforce"]) == 0
    assert "no backend source change to prove" in capsys.readouterr().out


@pytest.mark.unit
def test_main_skips_base_run_when_only_helpers_changed(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "changed_backend", lambda base: ([], ["backend/tests/_h.py"], S))
    monkeypatch.setattr(mod, "run_on_base", lambda *a: pytest.fail("should not run"))
    assert mod.main([]) == 0
    assert "no backend test_*.py file" in capsys.readouterr().out


@pytest.mark.unit
def test_main_warns_then_enforces_when_tests_pass_on_base(mod, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(mod, "changed_backend", lambda base: (T, [], S))
    monkeypatch.setattr(mod, "run_on_base", lambda *a: mod.BaseRun(0))
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert mod.main([]) == 0
    assert mod.main(["--enforce"]) == 1
    out = capsys.readouterr().out
    assert "::warning::Fail-to-pass: changed tests already pass" in out
    assert "::error::" in out
    assert "already pass on the base code" in summary.read_text()


class _Done:
    def __init__(self, returncode: int):
        self.returncode = returncode


@pytest.mark.unit
def test_run_on_base_copies_tests_and_helpers_and_reads_junit(mod, monkeypatch):
    commands: list[list[str]] = []

    def fake_run(cmd, cwd=None, check=False):
        commands.append(cmd)
        if cmd[:3] == ["git", "worktree", "add"]:
            (Path(cmd[-2]) / "backend" / "tests").mkdir(parents=True)
        if "pytest" in cmd:
            assert (Path(cwd) / "tests" / "test_check_fail_to_pass.py").is_file()
            assert (Path(cwd) / "tests" / "_paths.py").is_file()
            junit = next(c for c in cmd if c.startswith("--junitxml=")).split("=", 1)[1]
            Path(junit).write_text(
                '<testsuite><testcase name="a"><failure/></testcase></testsuite>'
            )
            return _Done(1)
        return _Done(0)

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    result = mod.run_on_base(
        "abc123", ["backend/tests/test_check_fail_to_pass.py"], ["backend/tests/_paths.py"]
    )
    assert result == mod.BaseRun(1, failures=1, import_errors=0)
    pytest_cmd = next(c for c in commands if "pytest" in c)
    assert pytest_cmd[-1] == "tests/test_check_fail_to_pass.py"
    assert commands[-1][:3] == ["git", "worktree", "remove"]


@pytest.mark.unit
def test_run_on_base_returns_none_when_checkout_fails(mod, monkeypatch):
    monkeypatch.setattr(mod.subprocess, "run", lambda cmd, cwd=None, check=False: _Done(128))
    assert mod.run_on_base("missing", T, []) is None


@pytest.mark.unit
def test_python_cmd_prefers_repo_venv(mod, monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    assert mod.python_cmd() == ["uv", "run", "python"]
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("")
    assert mod.python_cmd() == [str(tmp_path / ".venv" / "bin" / "python")]
