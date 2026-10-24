#!/usr/bin/env python3
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
PHONE = "+12025550100"
TITLE = "Upgrade check"

SEED = f"""
from django.contrib.auth import get_user_model
from community.models import Event
User = get_user_model()
user = User.objects.create_user(phone_number={PHONE!r}, password="upgrade-check", first_name="Upgrade")
Event.objects.create(title={TITLE!r}, created_by=user)
print("seeded", user.pk, flush=True)
"""

CHECK = f"""
import sys
from django.contrib.auth import get_user_model
from community.models import Event
User = get_user_model()
try:
    user = User.objects.get(phone_number={PHONE!r})
except User.DoesNotExist:
    sys.exit("user missing after upgrade")
try:
    event = Event.objects.get(title={TITLE!r}, created_by=user)
except Event.DoesNotExist:
    sys.exit("event missing after upgrade")

def assert_required(obj):
    for field in obj._meta.concrete_fields:
        if field.primary_key or field.null or getattr(field, "blank", False):
            continue
        if getattr(obj, field.attname) in (None, ""):
            sys.exit(f"{{obj.__class__.__name__}}.{{field.name}} is empty")

assert_required(user)
assert_required(event)
print("read back", user.pk, event.pk, flush=True)
"""


def database_name(url: str) -> str:
    return Path(unquote(urlparse(url).path)).name


def require_upgrade_database(url: str) -> None:
    name = database_name(url)
    if "upgrade" not in name:
        raise SystemExit(f"refusing to run: database {name!r} does not contain 'upgrade'")


def _uv(project: Path, directory: Path, *, sync: bool) -> list[str]:
    cmd = ["uv", "run", "--project", str(project), "--directory", str(directory), "--no-env-file"]
    if not sync:
        cmd.append("--no-sync")
    return [*cmd, "python", "manage.py"]


def _run(cmd: list[str], env: dict[str, str]) -> None:
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def _upgrade(main_wt: Path, env: dict[str, str]) -> None:
    same_lock = (ROOT / "uv.lock").read_bytes() == (main_wt / "uv.lock").read_bytes()
    main_env, project = env, ROOT
    if not same_lock:
        project = main_wt
        main_env = {**env, "UV_PROJECT_ENVIRONMENT": str(main_wt / ".venv")}
        main_env.pop("VIRTUAL_ENV", None)
    main_py = _uv(project, main_wt / "backend", sync=not same_lock)
    pr_py = _uv(ROOT, ROOT / "backend", sync=False)
    _run([*main_py, "migrate", "--noinput"], main_env)
    _run([*main_py, "shell", "--verbosity", "0", "-c", SEED], main_env)
    _run([*pr_py, "migrate", "--noinput"], env)
    _run([*pr_py, "shell", "--verbosity", "0", "-c", CHECK], env)


def main() -> None:
    url = os.environ.get("DATABASE_URL", "")
    require_upgrade_database(url)
    print(f"migration upgrade database: {database_name(url)}", flush=True)
    env = {**os.environ, "DATABASE_URL": url, "GIT_TERMINAL_PROMPT": "0"}
    env.setdefault("SECRET_KEY", "ci-only-not-used-in-prod")
    subprocess.run(["git", "fetch", "origin", "main"], cwd=ROOT, env=env, check=True)
    tmp = Path(tempfile.mkdtemp(prefix="pda-main-"))
    main_wt = tmp / "main"
    try:
        _run(["git", "worktree", "add", "--detach", str(main_wt), "origin/main"], env)
        _upgrade(main_wt, env)
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(main_wt)],
            cwd=ROOT,
            env=env,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        shutil.rmtree(tmp, ignore_errors=True)
    print("migration upgrade ok", flush=True)


if __name__ == "__main__":
    main()
