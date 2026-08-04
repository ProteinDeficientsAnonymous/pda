import logging
import mimetypes
import os
import posixpath
from io import BytesIO

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import FileResponse, Http404, HttpResponse
from django.utils._os import safe_join
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger("pda.media")

# Max display dimensions per photo kind — resize on upload so every consumer
# isn't downloading a multi-MB original just to shrink it with CSS.
AVATAR_MAX_DIMENSION = 512
EVENT_PHOTO_MAX_DIMENSION = 1600

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


def resize_image(photo: InMemoryUploadedFile, max_dimension: int) -> InMemoryUploadedFile:
    """Downscale an uploaded image to fit max_dimension. Best-effort: formats
    Pillow can't process (e.g. HEIC without a plugin) pass through unchanged
    rather than failing the upload.
    """
    try:
        image = Image.open(photo)
        image.verify()
        photo.seek(0)
        image = Image.open(photo)
    except (UnidentifiedImageError, OSError):
        return photo

    fmt = image.format
    if image.width <= max_dimension and image.height <= max_dimension:
        photo.seek(0)
        return photo

    if image.mode not in ("RGB", "RGBA", "L"):
        image = image.convert("RGBA" if "A" in image.mode else "RGB")
    image.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, format=fmt)
    buffer.seek(0)
    return InMemoryUploadedFile(
        buffer, photo.field_name, photo.name, photo.content_type, buffer.getbuffer().nbytes, None
    )


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
