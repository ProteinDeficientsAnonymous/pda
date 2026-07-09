import importlib.util
from pathlib import Path

import pytest


def _stamp_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "sqlite_dev_stamp.py"
    spec = importlib.util.spec_from_file_location("_sqlite_dev_stamp", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_seed_tree(root: Path) -> None:
    migrations = root / "backend" / "community" / "migrations"
    migrations.mkdir(parents=True)
    (migrations / "0001_initial.py").write_text("# v1\n")
    for rel in (
        "backend/community/management/commands/seed.py",
        "backend/community/management/commands/_seed_data.py",
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# seed\n")


@pytest.mark.unit
def test_is_current_false_when_db_or_stamp_missing(tmp_path):
    stamp = _stamp_module()
    db = tmp_path / "dev.db"
    assert stamp.is_current(db, root=tmp_path) is False
    db.write_bytes(b"sqlite")
    assert stamp.is_current(db, root=tmp_path) is False


@pytest.mark.unit
def test_write_stamp_marks_db_current(tmp_path):
    stamp = _stamp_module()
    _write_seed_tree(tmp_path)
    db = tmp_path / "dev.db"
    db.write_bytes(b"sqlite")
    stamp.write_stamp(db, root=tmp_path)
    assert stamp.stamp_path(db).read_text().strip() == stamp.fingerprint(root=tmp_path)
    assert stamp.is_current(db, root=tmp_path) is True


@pytest.mark.unit
def test_is_current_false_when_fingerprint_changes(tmp_path):
    stamp = _stamp_module()
    _write_seed_tree(tmp_path)
    db = tmp_path / "dev.db"
    db.write_bytes(b"sqlite")
    stamp.write_stamp(db, root=tmp_path)
    (tmp_path / "backend" / "community" / "migrations" / "0002_new.py").write_text("# v2\n")
    assert stamp.is_current(db, root=tmp_path) is False
