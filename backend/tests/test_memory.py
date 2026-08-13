import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from config.media_proxy import media_path
from config.memory import gunicorn_argv, media_path_calls, memory_profile_enabled, rss_kb, snapshot
from config.middleware import RequestLoggingMiddleware
from django.http import JsonResponse, StreamingHttpResponse
from django.test import Client, RequestFactory


@pytest.mark.unit
class TestRssKb:
    def test_reads_vmrss_from_proc_status(self, tmp_path: Path):
        status = tmp_path / "status"
        status.write_text("VmSize:\t  999999 kB\nVmRSS:\t   42100 kB\n")

        assert rss_kb(status_path=status) == 42100

    def test_falls_back_when_proc_status_missing(self, tmp_path: Path):
        missing = tmp_path / "nope"
        value = rss_kb(status_path=missing)
        assert isinstance(value, int)
        assert value >= 0


@pytest.mark.unit
class TestSnapshot:
    def test_includes_pid_and_rss(self):
        data = snapshot()
        assert data["pid"] > 0
        assert data["rss_kb"] >= 0
        assert "tracemalloc_tracing" in data
        assert isinstance(data["tracemalloc_top"], list)


@pytest.mark.unit
class TestGunicornArgv:
    def test_plain_gunicorn_uses_existing_venv_binary(self, monkeypatch):
        monkeypatch.delenv("PDA_MEMRAY", raising=False)
        argv = gunicorn_argv()
        gunicorn = Path(argv[0])
        assert gunicorn.is_absolute()
        assert gunicorn.name == "gunicorn"
        assert gunicorn.is_file()
        assert "config.asgi:application" in argv
        assert "--max-requests" in argv
        assert all(Path(part).name != "memray" for part in argv)

    def test_wraps_gunicorn_with_memray_when_enabled(self, monkeypatch):
        monkeypatch.setenv("PDA_MEMRAY", "1")
        monkeypatch.setenv("PDA_MEMRAY_OUTPUT", "/tmp/custom.bin")
        argv = gunicorn_argv()
        memray = Path(argv[0])
        gunicorn = Path(argv[6])
        assert memray.is_absolute()
        assert memray.name == "memray"
        assert memray.is_file()
        assert argv[1:6] == ["run", "--follow-fork", "--compress", "--output", "/tmp/custom.bin"]
        assert gunicorn.is_absolute()
        assert gunicorn.name == "gunicorn"
        assert gunicorn.is_file()


@pytest.mark.unit
class TestMemoryProfileFlag:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("PDA_MEMORY_PROFILE", raising=False)
        assert memory_profile_enabled() is False

    def test_enabled_when_set_to_one(self, monkeypatch):
        monkeypatch.setenv("PDA_MEMORY_PROFILE", "1")
        assert memory_profile_enabled() is True


@pytest.mark.unit
class TestRequestLoggingRss:
    @pytest.fixture(autouse=True)
    def _enable_propagation(self):
        pda_logger = logging.getLogger("pda")
        original = pda_logger.propagate
        pda_logger.propagate = True
        yield
        pda_logger.propagate = original

    def test_omits_rss_when_profile_disabled(self, caplog, monkeypatch):
        monkeypatch.delenv("PDA_MEMORY_PROFILE", raising=False)
        factory = RequestFactory()
        request = factory.get("/api/community/events/x/")

        middleware = RequestLoggingMiddleware(lambda _r: JsonResponse({"ok": True}))
        with caplog.at_level(logging.INFO, logger="pda.middleware"):
            middleware(request)

        record = caplog.records[0]
        assert not hasattr(record, "rss_kb")

    def test_logs_rss_when_profile_enabled(self, caplog, monkeypatch):
        monkeypatch.setenv("PDA_MEMORY_PROFILE", "1")
        factory = RequestFactory()
        request = factory.get("/api/community/events/x/")

        middleware = RequestLoggingMiddleware(lambda _r: JsonResponse({"ok": True}))
        with caplog.at_level(logging.INFO, logger="pda.middleware"):
            middleware(request)

        record = caplog.records[0]
        assert record.rss_kb >= 0  # type: ignore[attr-defined]
        assert hasattr(record, "rss_delta_kb")
        assert record.media_path_calls == 0  # type: ignore[attr-defined]
        body = JsonResponse({"ok": True})
        assert record.response_bytes == len(body.content)  # type: ignore[attr-defined]

    def test_counts_media_path_calls_for_the_request(self, caplog, monkeypatch):
        monkeypatch.setenv("PDA_MEMORY_PROFILE", "1")
        factory = RequestFactory()
        request = factory.get("/api/community/events/x/")
        field = SimpleNamespace(url="https://s3.example/a.jpg")

        def get_response(_r):
            media_path(field)
            media_path(field)
            media_path(None)
            return JsonResponse({"ok": True})

        middleware = RequestLoggingMiddleware(get_response)
        with caplog.at_level(logging.INFO, logger="pda.middleware"):
            middleware(request)

        assert caplog.records[0].media_path_calls == 3  # type: ignore[attr-defined]

    def test_omits_response_bytes_for_streaming(self, caplog, monkeypatch):
        monkeypatch.setenv("PDA_MEMORY_PROFILE", "1")
        factory = RequestFactory()
        request = factory.get("/api/notifications/stream/")

        middleware = RequestLoggingMiddleware(
            lambda _r: StreamingHttpResponse(iter([b"data: x\n\n"]))
        )
        with caplog.at_level(logging.INFO, logger="pda.middleware"):
            middleware(request)

        assert not hasattr(caplog.records[0], "response_bytes")


@pytest.mark.unit
class TestMediaPathCalls:
    def test_does_not_count_when_profile_disabled(self, monkeypatch):
        monkeypatch.delenv("PDA_MEMORY_PROFILE", raising=False)
        before = media_path_calls()
        media_path(SimpleNamespace(url="https://s3.example/a.jpg"))
        assert media_path_calls() == before


@pytest.mark.django_db
class TestMemorySnapshotView:
    def test_404_when_profile_disabled(self, monkeypatch):
        monkeypatch.delenv("PDA_MEMORY_PROFILE", raising=False)
        response = Client().get("/api/community/debug/memory/")
        assert response.status_code == 404

    def test_returns_snapshot_when_profile_enabled(self, monkeypatch):
        monkeypatch.setenv("PDA_MEMORY_PROFILE", "1")
        response = Client().get("/api/community/debug/memory/")
        assert response.status_code == 200
        data = response.json()
        assert data["rss_kb"] >= 0
        assert "pid" in data
