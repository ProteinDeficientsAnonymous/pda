import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_diff_tampering.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_diff_tampering", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    # dataclasses resolve their module through sys.modules
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _diff(path: str, removed: list[str], added: list[str], *, deleted: bool = False) -> str:
    new = "/dev/null" if deleted else f"b/{path}"
    body = [f"-{line}" for line in removed] + [f"+{line}" for line in added]
    return "\n".join(
        [f"diff --git a/{path} b/{path}", f"--- a/{path}", f"+++ {new}", "@@ -1 +1 @@", *body]
    )


@pytest.mark.unit
def test_removed_python_test_and_assertions_are_flagged():
    mod = _load_module()
    diff = _diff(
        "backend/tests/test_events.py",
        [
            "def test_rsvp_limit():",
            "    assert resp.status_code == 403",
            "    assert Event.objects.count() == 1",
        ],
        [],
    )
    findings = mod.analyse(mod.parse_diff(diff))
    assert any("1 test(s) removed" in f for f in findings)
    assert any("net 2 assertion(s) removed" in f for f in findings)


@pytest.mark.unit
def test_rewritten_assertion_with_same_count_is_not_flagged():
    mod = _load_module()
    diff = _diff(
        "frontend/src/screens/Home.test.tsx",
        ["  expect(screen.getByText('old')).toBeInTheDocument();"],
        ["  expect(screen.getByText('new')).toBeInTheDocument();"],
    )
    assert mod.analyse(mod.parse_diff(diff)) == []


@pytest.mark.unit
def test_trivially_true_assertion_is_flagged():
    mod = _load_module()
    diff = _diff("backend/tests/test_auth.py", ["    assert user.is_active"], ["    assert True"])
    findings = mod.analyse(mod.parse_diff(diff))
    assert any("trivially-true assertion added" in f for f in findings)


@pytest.mark.unit
def test_deleted_test_file_counts_removed_tests():
    mod = _load_module()
    diff = _diff(
        "frontend/e2e/login.spec.ts",
        ["test('logs in', async () => {", "  expect(x).toBe(1);"],
        [],
        deleted=True,
    )
    findings = mod.analyse(mod.parse_diff(diff))
    assert any("frontend/e2e/login.spec.ts: 1 test(s) removed" in f for f in findings)


@pytest.mark.unit
def test_removed_sql_comment_line_is_not_read_as_a_header():
    mod = _load_module()
    diff = _diff("backend/tests/test_sql.py", ["-- select 1", "    assert rows"], [])
    deltas = mod.parse_diff(diff)
    assert deltas["backend/tests/test_sql.py"].removed == ["-- select 1", "    assert rows"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/ci.yml",
        "Makefile",
        ".claude/settings.json",
        "scripts/check_anti_tampering.py",
    ],
)
def test_gate_config_changes_are_flagged(path):
    mod = _load_module()
    findings = mod.analyse(mod.parse_diff(_diff(path, ["old"], ["new"])))
    assert findings == [f"{path}: gate config changed — needs a human reviewer"]


@pytest.mark.unit
def test_non_test_non_gate_file_is_ignored():
    mod = _load_module()
    diff = _diff("backend/community/views.py", ["    assert x", "def test_helper():"], [])
    assert mod.analyse(mod.parse_diff(diff)) == []


@pytest.mark.unit
def test_main_warns_in_observe_mode_and_fails_when_enforced(monkeypatch, capsys):
    mod = _load_module()
    diff = _diff("backend/tests/test_x.py", ["def test_a():", "    assert a"], [])
    monkeypatch.setattr(mod, "branch_diff", lambda base: diff)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert mod.main(["--base", "origin/main"]) == 0
    assert mod.main(["--base", "origin/main", "--enforce"]) == 1
    assert "1 test(s) removed" in capsys.readouterr().out


@pytest.mark.unit
def test_main_writes_annotations_and_step_summary_in_ci(monkeypatch, capsys, tmp_path):
    mod = _load_module()
    summary = tmp_path / "summary.md"
    monkeypatch.setattr(mod, "branch_diff", lambda base: _diff("Makefile", ["a"], ["b"]))
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert mod.main([]) == 0
    assert "::warning file=Makefile::gate config changed" in capsys.readouterr().out
    assert "`Makefile: gate config changed" in summary.read_text()


@pytest.mark.unit
def test_main_passes_on_clean_diff(monkeypatch, capsys):
    mod = _load_module()
    monkeypatch.setattr(mod, "branch_diff", lambda base: "")
    assert mod.main(["--enforce"]) == 0
    assert "No weakened tests" in capsys.readouterr().out
