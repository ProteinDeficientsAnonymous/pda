import mimetypes

from django.core.files.storage import default_storage
from django.http import FileResponse, Http404


def media_path(field) -> str:
    """Return a relative /media/ URL for a FileField, or '' if empty."""
    if not field:
        return ""
    return f"/media/{field.name}"


def serve_media(request, path):
    if not default_storage.exists(path):
        raise Http404
    f = default_storage.open(path)
    content_type, _ = mimetypes.guess_type(path)
    response = FileResponse(f, content_type=content_type or "application/octet-stream")
    response["Cache-Control"] = "public, max-age=86400, immutable"
    return response
