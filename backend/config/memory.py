import os
import resource
import shutil
import sys
import tracemalloc
from contextvars import ContextVar
from pathlib import Path

_GUNICORN = [
    "gunicorn",
    "--config",
    "python:config.gunicorn_conf",
    "config.asgi:application",
]

_media_path_calls: ContextVar[int] = ContextVar("pda_media_path_calls", default=0)


def memory_profile_enabled() -> bool:
    return os.environ.get("PDA_MEMORY_PROFILE") == "1"


def reset_media_path_calls() -> None:
    _media_path_calls.set(0)


def record_media_path_call() -> None:
    _media_path_calls.set(_media_path_calls.get() + 1)


def media_path_calls() -> int:
    return _media_path_calls.get()


def rss_kb(status_path: str = "/proc/self/status") -> int:
    try:
        with open(status_path) as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except (FileNotFoundError, OSError, ValueError, IndexError):
        pass
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return rss // 1024
    return rss


def ensure_tracemalloc() -> None:
    if memory_profile_enabled() and not tracemalloc.is_tracing():
        tracemalloc.start()


def snapshot(*, top: int = 15) -> dict:
    data: dict[str, object] = {
        "pid": os.getpid(),
        "rss_kb": rss_kb(),
        "tracemalloc_tracing": tracemalloc.is_tracing(),
        "tracemalloc_top": [],
    }
    if not tracemalloc.is_tracing():
        return data
    stats = tracemalloc.take_snapshot().statistics("lineno")[:top]
    data["tracemalloc_top"] = [
        {"size_kb": round(s.size / 1024, 1), "count": s.count, "location": str(s.traceback)}
        for s in stats
    ]
    return data


def _venv_bin(name: str) -> str:
    extra = [str(Path(sys.executable).resolve().parent), str(Path(sys.prefix) / "bin")]
    if os.environ.get("VIRTUAL_ENV"):
        extra.append(str(Path(os.environ["VIRTUAL_ENV"]) / "bin"))
    found = shutil.which(name, path=os.pathsep.join([*extra, os.environ.get("PATH", "")]))
    if not found:
        raise FileNotFoundError(name)
    return found


def gunicorn_argv() -> list[str]:
    gunicorn = [_venv_bin("gunicorn"), *_GUNICORN[1:]]
    if os.environ.get("PDA_MEMRAY") != "1":
        return gunicorn
    output = os.environ.get("PDA_MEMRAY_OUTPUT", "/tmp/memray.bin")
    return [
        _venv_bin("memray"),
        "run",
        "--follow-fork",
        "--compress",
        "--output",
        output,
        *gunicorn,
    ]
