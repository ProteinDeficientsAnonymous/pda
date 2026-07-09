import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "dev_pg_db.sh"


@pytest.mark.unit
def test_dev_pg_db_fingerprint_is_stable_sha256():
    runs = [
        subprocess.run(
            [str(SCRIPT), "fingerprint"],
            check=True,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        ).stdout.strip()
        for _ in range(2)
    ]
    assert runs[0] == runs[1]
    assert len(runs[0]) == 64
