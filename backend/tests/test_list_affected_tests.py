import importlib.util
import sys

import pytest

from tests._paths import REPO_ROOT


@pytest.fixture
def mod():
    path = REPO_ROOT / "scripts" / "list_affected_tests.py"
    spec = importlib.util.spec_from_file_location("list_affected_tests", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
@pytest.mark.parametrize(
    ("diff_path", "expected"),
    [
        ("backend/tests/test_auth.py", "tests/test_auth.py"),
        ("backend/tests/users/test_x.py", "tests/users/test_x.py"),
        ("backend/tests/_helpers.py", None),
        ("backend/community/views.py", None),
    ],
)
def test_changed_test_keeps_its_subdirectory(mod, diff_path, expected):
    assert mod._test_path_from_diff(diff_path) == expected


@pytest.mark.unit
def test_users_source_change_runs_the_users_test_directory(mod):
    collected = mod._classify_and_collect(["backend/users/_transitions.py"])
    assert collected is not None
    assert "tests/users/" in collected
