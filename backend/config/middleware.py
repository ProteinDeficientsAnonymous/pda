import logging
import time

logger = logging.getLogger("pda.middleware")


class CrossOriginIsolationMiddleware:
    """Sets COOP/COEP headers on HTML responses.

    Required for Flutter's Skwasm renderer to use multi-threaded mode
    (SharedArrayBuffer), which enables the smaller skwasm.wasm (~3.4MB)
    instead of skwasm_heavy.wasm (~4.9MB) or canvaskit.wasm (~6.8MB).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if "text/html" in response.get("Content-Type", ""):
            response["Cross-Origin-Opener-Policy"] = "same-origin"
            response["Cross-Origin-Embedder-Policy"] = "require-corp"
        return response


class RequestLoggingMiddleware:
    """Logs HTTP method, path, status code, and duration for each request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/static/"):
            return self.get_response(request)

        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000

        user = getattr(request, "user", None)
        user_id = str(user.pk) if user and getattr(user, "is_authenticated", False) else None

        logger.info(
            "%s %s %s %.0fms",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            extra={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "user_id": user_id,
            },
        )

        return response
