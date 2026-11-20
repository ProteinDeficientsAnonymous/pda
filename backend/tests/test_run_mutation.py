import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_mutation.py"


@pytest.fixture
def mod(monkeypatch):
    spec = importlib.util.spec_from_file_location("run_mutation", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    return module


def _done(stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")


@pytest.mark.unit
def test_changed_backend_files_skips_tests_and_migrations(mod, monkeypatch):
    out = "backend/community/views.py\nbackend/tests/test_x.py\nbackend/users/migrations/0001.py\nbackend/a.txt\n"
    monkeypatch.setattr(mod.subprocess, "check_output", lambda *a, **k: out)
    assert mod.changed_backend_files("origin/main") == ["community/views.py"]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("listed", "expected"),
    [
        ("tests/test_a.py\ntests/test_b.py\n", ["tests/test_a.py", "tests/test_b.py"]),
        ("__FULL__\n", ["tests/"]),
        ("", ["tests/"]),
    ],
)
def test_affected_tests_falls_back_to_the_full_suite(mod, monkeypatch, listed, expected):
    monkeypatch.setattr(mod.subprocess, "check_output", lambda *a, **k: listed)
    assert mod.affected_tests("origin/main") == expected


@pytest.mark.unit
def test_no_changed_files_skips_mutation(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "changed_backend_files", lambda base: [])
    assert mod.main([]) == 0
    assert "No changed backend domain files" in capsys.readouterr().out


@pytest.mark.unit
def test_survivors_are_reported_and_fail_only_when_enforced(mod, monkeypatch, tmp_path, capsys):
    calls: list[list[str]] = []

    def fake_mutmut(*args):
        calls.append(list(args))
        if args[0] == "result-ids":
            return _done("3 7\n")
        return _done(f"--- mutant {args[1]}")

    monkeypatch.setattr(mod, "_mutmut", fake_mutmut)
    monkeypatch.setattr(mod.subprocess, "run", lambda cmd, **k: calls.append(cmd))
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert mod.main(["community/views.py", "--tests", "tests/test_views.py"]) == 0
    assert mod.main(["community/views.py", "--tests", "tests/test_views.py", "--enforce"]) == 1
    run_cmd = next(c for c in calls if "run" in c and "--runner" in c)
    assert run_cmd[run_cmd.index("--paths-to-mutate") + 1] == "community/views.py"
    assert run_cmd[-1].endswith("tests/test_views.py")
    out = capsys.readouterr().out
    assert "2 surviving mutant(s)" in out
    assert "--- mutant 7" in out
    assert "2 surviving mutant(s)" in summary.read_text()


@pytest.mark.unit
def test_report_truncates_long_survivor_lists(mod, monkeypatch):
    monkeypatch.setattr(mod, "_mutmut", lambda *a: _done("diff"))
    text = mod.report([str(i) for i in range(mod.MAX_SHOWN + 5)])
    assert "…and 5 more" in text
    assert text.count("```diff") == mod.MAX_SHOWN


@pytest.mark.unit
def test_no_survivors_passes_when_enforced(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_mutmut", lambda *a: _done(""))
    monkeypatch.setattr(mod.subprocess, "run", lambda cmd, **k: None)
    assert mod.main(["community/views.py", "--tests", "tests/", "--enforce"]) == 0
    assert "no surviving mutants" in capsys.readouterr().out
