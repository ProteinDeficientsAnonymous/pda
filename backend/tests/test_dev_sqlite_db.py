import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "dev_sqlite_db.sh"


@pytest.mark.unit
def test_dev_sqlite_db_stamp_roundtrip(tmp_path):
    db = tmp_path / "dev.db"
    db.write_bytes(b"sqlite")

    subprocess.run([str(SCRIPT), "write", str(db)], check=True, cwd=REPO_ROOT)
    assert subprocess.run([str(SCRIPT), "check", str(db)], cwd=REPO_ROOT).returncode == 0

    fp = subprocess.run(
        [str(SCRIPT), "fingerprint"],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    ).stdout.strip()
    assert len(fp) == 64
