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


@pytest.mark.unit
@pytest.mark.parametrize(
    ("source", "expected_test"),
    [
        ("backend/mcp_gateway/tools/events_read.py", "tests/test_mcp_events_read.py"),
        (
            "backend/mcp_gateway/management/commands/prune_mcp_oauth.py",
            "tests/test_prune_mcp_oauth.py",
        ),
        ("backend/audit/models.py", "tests/test_audit_persistence.py"),
        ("backend/audit/api.py", "tests/users/test_user_transition_audits.py"),
    ],
)
def test_app_source_maps_to_its_bundle_not_the_full_suite(mod, source, expected_test):
    collected = mod._classify_and_collect([source])
    assert collected is not None
    assert expected_test in collected


@pytest.mark.unit
def test_every_bundle_path_exists(mod):
    for prefix, bundle in mod.BACKEND_BUNDLES:
        assert bundle, prefix
        assert all((mod.BACKEND_DIR / p).exists() for p in bundle), prefix


@pytest.mark.unit
def test_helper_change_runs_tests_importing_it_through_other_helpers(mod):
    collected = mod._classify_and_collect(["backend/tests/_mcp_helpers.py"])
    assert collected is not None
    assert "tests/test_mcp_server.py" in collected
    # imports _mcp_helpers only via tests._mcp_provider
    assert "tests/test_mcp_provider_race.py" in collected
    assert not any(p.startswith("tests/users") for p in collected)


@pytest.mark.unit
def test_helper_used_by_the_root_conftest_runs_the_full_suite(mod):
    assert mod._classify_and_collect(["backend/tests/_users.py"]) is None


@pytest.mark.unit
def test_nested_conftest_runs_its_directory(mod):
    assert mod._classify_and_collect(["backend/tests/users/conftest.py"]) == {"tests/users/"}


@pytest.mark.unit
def test_root_conftest_still_runs_the_full_suite(mod):
    assert mod._classify_and_collect(["backend/tests/conftest.py"]) is None
