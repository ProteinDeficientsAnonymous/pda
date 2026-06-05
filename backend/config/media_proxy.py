import logging
import mimetypes
import os
import posixpath

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponse
from django.utils._os import safe_join

logger = logging.getLogger("pda.media")

# Content types we're willing to serve inline. Everything else (notably
# text/html and image/svg+xml, which can execute JS on the app origin) is
# forced to download via Content-Disposition: attachment.
_INLINE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/avif",
        "application/pdf",
    }
)


def media_path(field) -> str:
    """Return a relative /media/ URL for a FileField, or '' if empty."""
    if not field:
        return ""
    return f"/media/{field.name}"


def _is_safe_path(path: str) -> bool:
    """Reject traversal, absolute paths, backslashes, and null bytes."""
    if not path or "\x00" in path or "\\" in path:
        return False
    if path.startswith("/"):
        return False
    # Normalize with posix semantics; a normalized path that escapes the root
    # (starts with '..') or stays at '.' is rejected.
    normalized = posixpath.normpath(path)
    if normalized.startswith("..") or normalized == "." or os.path.isabs(normalized):
        return False
    return True


def _confined_to_media_root(path: str) -> bool:
    """For filesystem storage, ensure the resolved path stays under MEDIA_ROOT.

    Non-filesystem backends (e.g. S3/B2) have no local MEDIA_ROOT to confine
    to; the string-level checks in `_is_safe_path` are the guard there.
    """
    media_root = getattr(settings, "MEDIA_ROOT", None)
    if not media_root:
        return True
    try:
        candidate = safe_join(str(media_root), path)
    except (ValueError, SuspiciousOperation):
        return False
    real_root = os.path.realpath(str(media_root))
    real_candidate = os.path.realpath(candidate)
    return os.path.commonpath([real_root, real_candidate]) == real_root


def serve_media(request, path):
    if not _is_safe_path(path) or not _confined_to_media_root(path):
        logger.warning("media_proxy rejected unsafe path", extra={"media_path": path})
        raise Http404

    try:
        if not default_storage.exists(path):
            raise Http404
        f = default_storage.open(path)
    except Http404:
        raise
    except Exception:
        logger.exception("media_proxy failed to open storage object", extra={"media_path": path})
        return HttpResponse("Unable to serve media.", status=502, content_type="text/plain")

    content_type, _ = mimetypes.guess_type(path)
    content_type = content_type or "application/octet-stream"

    response = FileResponse(f, content_type=content_type)
    response["Cache-Control"] = "public, max-age=86400, immutable"
    # Prevent browsers from MIME-sniffing an uploaded file into something
    # executable (e.g. treating a .txt as HTML).
    response["X-Content-Type-Options"] = "nosniff"
    # Images/PDFs may render inline; anything else (html/svg/scripts) is forced
    # to download so it can't execute JS on the app origin.
    disposition = "inline" if content_type in _INLINE_CONTENT_TYPES else "attachment"
    response["Content-Disposition"] = disposition
    return response
