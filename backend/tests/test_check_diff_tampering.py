import importlib.util
import sys

import pytest

from tests._paths import REPO_ROOT

SCRIPT_PATH = REPO_ROOT / "scripts" / "check_diff_tampering.py"


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
@pytest.mark.parametrize(
    "line",
    [
        "    assert True, 'covered'",
        "    assert 1 == 1",
        "    assert resp.ok or True",
        "  expect(1)" + ".toBe(1);",
        "  expect('a')" + ".toEqual('a');",
    ],
)
def test_trivially_true_assertion_variants_are_flagged(line):
    mod = _load_module()
    diff = _diff("frontend/src/a.test.ts", ["  expect(x).toBe(2);"], [line])
    findings = mod.analyse(mod.parse_diff(diff))
    assert any("trivially-true assertion added" in f for f in findings)


@pytest.mark.unit
def test_moving_tests_between_files_is_not_flagged():
    mod = _load_module()
    moved = ["def test_rsvp_limit():", "    assert resp.status_code == 403"]
    diff = "\n".join(
        [
            _diff("backend/tests/test_events.py", moved, []),
            _diff("backend/tests/events/test_rsvp.py", [], moved),
        ]
    )
    assert mod.analyse(mod.parse_diff(diff)) == []


@pytest.mark.unit
def test_net_loss_across_files_is_reported_per_losing_file():
    mod = _load_module()
    diff = "\n".join(
        [
            _diff("backend/tests/test_a.py", ["def test_a():", "def test_b():"], []),
            _diff("backend/tests/test_b.py", [], ["def test_c():"]),
        ]
    )
    assert mod.analyse(mod.parse_diff(diff)) == ["backend/tests/test_a.py: 2 test(s) removed"]


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
        "pyproject.toml",
        "frontend/package.json",
        "frontend/.oxfmtrc.json",
        "frontend/tsconfig.app.json",
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
def test_missing_base_is_a_notice_in_observe_mode(monkeypatch, capsys):
    mod = _load_module()

    def fail(base):
        raise mod.subprocess.CalledProcessError(128, "git diff")

    monkeypatch.setattr(mod, "branch_diff", fail)
    assert mod.main(["--base", "nope"]) == 0
    assert mod.main(["--base", "nope", "--enforce"]) == 1
    assert "diff tampering check skipped" in capsys.readouterr().out


@pytest.mark.unit
def test_main_passes_on_clean_diff(monkeypatch, capsys):
    mod = _load_module()
    monkeypatch.setattr(mod, "branch_diff", lambda base: "")
    assert mod.main(["--enforce"]) == 0
    assert "No weakened tests" in capsys.readouterr().out
