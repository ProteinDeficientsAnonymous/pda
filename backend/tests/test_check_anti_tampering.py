import importlib.util
from pathlib import Path

import pytest

from tests._paths import REPO_ROOT

SCRIPT_PATH = REPO_ROOT / "scripts" / "check_anti_tampering.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_anti_tampering", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_scan_text_flags_lint_and_type_suppressions():
    mod = _load_module()
    findings = mod.scan_text(
        "backend/community/views.py",
        "x = foo()  # noqa: F401\ny = bar()  # type: ignore[arg-type]\n",
    )
    assert len(findings) == 2
    assert any("noqa" in f for f in findings)
    assert any("type: ignore" in f for f in findings)


@pytest.mark.unit
def test_scan_text_flags_skipped_tests_but_allows_skipif():
    mod = _load_module()
    findings = mod.scan_text(
        "backend/tests/test_events.py",
        "@pytest.mark.skip(reason='flaky')\n@pytest.mark.skipif(True, reason='env')\n",
    )
    assert len(findings) == 1
    assert "skipped pytest test" in findings[0]


@pytest.mark.unit
def test_scan_tree_reports_repo_violations(tmp_path: Path):
    mod = _load_module()
    (tmp_path / "backend").mkdir()
    bad = tmp_path / "backend" / "bad.py"
    bad.write_text("x = 1  # noqa: F401\n", encoding="utf-8")
    clean = tmp_path / "backend" / "clean.py"
    clean.write_text("x = 1\n", encoding="utf-8")
    findings = mod.scan_tree(tmp_path)
    assert len(findings) == 1
    assert "backend/bad.py" in findings[0]


@pytest.mark.unit
def test_repo_has_no_anti_tampering_violations():
    mod = _load_module()
    findings = mod.scan_tree(REPO_ROOT)
    assert findings == [], "\n".join(findings)
