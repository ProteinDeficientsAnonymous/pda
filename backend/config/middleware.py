import logging
import time

from config.memory import (
    ensure_tracemalloc,
    media_path_calls,
    memory_profile_enabled,
    reset_media_path_calls,
    rss_kb,
)

logger = logging.getLogger("pda.middleware")


def _response_bytes(response) -> int | None:
    if getattr(response, "streaming", False):
        return None
    content = getattr(response, "content", None)
    if isinstance(content, (bytes, memoryview)):
        return len(content)
    return None


class RequestLoggingMiddleware:
    """Logs HTTP method, path, status code, and duration for each request."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._last_rss_kb: int | None = None

    def _memory_extras(self, response) -> dict:
        current = rss_kb()
        extras = {
            "rss_kb": current,
            "rss_delta_kb": current - (self._last_rss_kb or current),
            "media_path_calls": media_path_calls(),
        }
        self._last_rss_kb = current
        size = _response_bytes(response)
        if size is not None:
            extras["response_bytes"] = size
        return extras

    def __call__(self, request):
        if request.path.startswith("/static/"):
            return self.get_response(request)

        profile = memory_profile_enabled()
        if profile:
            reset_media_path_calls()
            ensure_tracemalloc()

        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000

        user = getattr(request, "user", None)
        user_id = str(user.pk) if user and getattr(user, "is_authenticated", False) else None

        extra = {
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "user_id": user_id,
        }
        if profile:
            extra.update(self._memory_extras(response))

        logger.info(
            "%s %s %s %.0fms",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            extra=extra,
        )

        return response
