import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_anti_tampering.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_anti_tampering", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_scan_diff_flags_lint_and_type_suppressions():
    mod = _load_module()
    diff = "\n".join(
        [
            "+++ b/backend/community/views.py",
            "@@ -1,3 +1,5 @@",
            "+x = foo()  # noqa: F401",
            "+y = bar()  # type: ignore[arg-type]",
            "+++ b/frontend/src/App.tsx",
            "@@ -10,2 +10,4 @@",
            "+// @ts-expect-error",
            "+// oxlint-disable-next-line no-console",
        ]
    )
    findings = mod.scan_diff(diff)
    assert len(findings) == 4
    assert any("backend/community/views.py" in f and "noqa" in f for f in findings)
    assert any("backend/community/views.py" in f and "type: ignore" in f for f in findings)
    assert any("frontend/src/App.tsx" in f and "@ts-expect-error" in f for f in findings)
    assert any("frontend/src/App.tsx" in f and "oxlint-disable" in f for f in findings)


@pytest.mark.unit
def test_scan_diff_flags_skipped_tests():
    mod = _load_module()
    diff = "\n".join(
        [
            "+++ b/backend/tests/test_events.py",
            "@@ -1,2 +1,4 @@",
            "+@pytest.mark.skip(reason='flaky')",
            "+++ b/frontend/src/App.test.tsx",
            "@@ -1,2 +1,4 @@",
            "+it.skip('renders', () => {})",
        ]
    )
    findings = mod.scan_diff(diff)
    assert len(findings) == 2


@pytest.mark.unit
def test_scan_diff_ignores_removed_lines_and_clean_additions():
    mod = _load_module()
    diff = "\n".join(
        [
            "+++ b/backend/community/views.py",
            "@@ -1,3 +1,3 @@",
            "-x = foo()  # noqa: F401",
            "+x = foo()",
        ]
    )
    assert mod.scan_diff(diff) == []
