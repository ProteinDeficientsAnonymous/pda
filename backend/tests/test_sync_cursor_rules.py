import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "sync_cursor_rules.py"
_spec = importlib.util.spec_from_file_location("sync_cursor_rules", _SCRIPT)
scr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scr)

_SCOPED = '---\npaths:\n  - "**/*.py"\n  - "frontend/**"\n---\n\n# Scoped Rule\n\nbody\n'
_ALWAYS = "# Always Rule\n\nbody\n"


@pytest.fixture
def dirs(tmp_path):
    rules, cursor = tmp_path / "claude-rules", tmp_path / "cursor-rules"
    rules.mkdir()
    cursor.mkdir()
    (rules / "scoped.md").write_text(_SCOPED)
    (rules / "always.md").write_text(_ALWAYS)
    (cursor / scr.SUMMARY_NAME).write_text("summary of `always.md`\n")
    return rules, cursor


@pytest.mark.unit
def test_expected_stubs_scoped_rule_maps_paths_to_globs(dirs):
    rules, _ = dirs
    stubs = scr.expected_stubs(rules)
    assert list(stubs) == ["claude-rule-scoped.mdc"]
    stub = stubs["claude-rule-scoped.mdc"]
    assert "description: Scoped Rule\n" in stub
    assert "globs: **/*.py, frontend/**\n" in stub
    assert "alwaysApply: false\n" in stub
    assert "`.claude/rules/scoped.md`" in stub


@pytest.mark.unit
def test_find_problems_after_write_returns_none(dirs):
    rules, cursor = dirs
    scr.write_stubs(rules, cursor)
    assert scr.find_problems(rules, cursor) == []


@pytest.mark.unit
def test_find_problems_paths_changed_reports_stale_stub(dirs):
    rules, cursor = dirs
    scr.write_stubs(rules, cursor)
    (rules / "scoped.md").write_text(_SCOPED.replace("frontend/**", "web/**"))
    assert scr.find_problems(rules, cursor) == ["stale: claude-rule-scoped.mdc"]


@pytest.mark.unit
def test_find_problems_rule_deleted_reports_orphan_and_write_removes_it(dirs):
    rules, cursor = dirs
    scr.write_stubs(rules, cursor)
    (rules / "scoped.md").unlink()
    assert scr.find_problems(rules, cursor) == ["orphan: claude-rule-scoped.mdc"]
    scr.write_stubs(rules, cursor)
    assert not (cursor / "claude-rule-scoped.mdc").exists()


@pytest.mark.unit
def test_find_problems_always_on_rule_missing_from_summary(dirs):
    rules, cursor = dirs
    scr.write_stubs(rules, cursor)
    (rules / "new-always.md").write_text(_ALWAYS)
    assert scr.find_problems(rules, cursor) == [f"not in {scr.SUMMARY_NAME}: new-always.md"]
