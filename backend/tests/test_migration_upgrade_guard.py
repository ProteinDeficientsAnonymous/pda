import importlib.util
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_migration_upgrade.py"
_spec = importlib.util.spec_from_file_location("check_migration_upgrade", _PATH)
guard = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(guard)


@pytest.mark.unit
def test_database_name_ignores_credentials():
    assert guard.database_name("postgresql://pda:upgrade@localhost:5432/pda") == "pda"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("url", "allowed"),
    [
        ("postgresql://pda:pda@localhost:5432/pda_upgrade", True),
        ("postgresql://pda:upgrade@localhost:5432/pda", False),
        ("sqlite:////tmp/pda_upgrade_local.db", True),
        ("sqlite:////tmp/dev.db", False),
        ("", False),
    ],
)
def test_require_upgrade_database_checks_name_only(url, allowed):
    if allowed:
        guard.require_upgrade_database(url)
        return
    with pytest.raises(SystemExit):
        guard.require_upgrade_database(url)
