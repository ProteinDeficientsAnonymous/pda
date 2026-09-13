import io

from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageSequence, UnidentifiedImageError

EVENT_MAX_EDGE = 1200
AVATAR_MAX_EDGE = 512
_QUALITY = 80


_PIL_OPEN_ERRORS = (UnidentifiedImageError, OSError, Image.DecompressionBombError)


def maybe_webp_from_animated_gif(data: bytes) -> bytes | None:
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.format != "GIF" or getattr(im, "n_frames", 1) <= 1:
                return None
            frames = []
            durations = []
            for frame in ImageSequence.Iterator(im):
                frames.append(frame.convert("RGBA"))
                durations.append(frame.info.get("duration", 100))
            loop = im.info.get("loop", 0)
        buf = io.BytesIO()
        frames[0].save(
            buf,
            format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=loop,
            quality=_QUALITY,
            method=4,
        )
        webp = buf.getvalue()
    except _PIL_OPEN_ERRORS:
        return None
    if len(webp) >= len(data):
        return None
    return webp


def maybe_jpeg_from_still(data: bytes, max_edge: int) -> bytes | None:
    try:
        im = Image.open(io.BytesIO(data))
    except _PIL_OPEN_ERRORS:
        return None
    try:
        with im:
            if getattr(im, "n_frames", 1) > 1:
                return None
            rgb = _as_rgb(im)
            rgb.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            rgb.save(buf, format="JPEG", quality=_QUALITY, optimize=True)
        jpeg = buf.getvalue()
    except _PIL_OPEN_ERRORS:
        return None
    if len(jpeg) >= len(data):
        return None
    return jpeg


def compress_photo(data: bytes, max_edge: int) -> tuple[bytes, str] | None:
    webp = maybe_webp_from_animated_gif(data)
    if webp is not None:
        return webp, "webp"
    jpeg = maybe_jpeg_from_still(data, max_edge)
    if jpeg is not None:
        return jpeg, "jpg"
    return None


def stored_photo(raw: bytes, name: str, max_edge: int) -> tuple[ContentFile, str]:
    result = compress_photo(raw, max_edge)
    if result is None:
        return ContentFile(raw), name.rsplit(".", 1)[-1] if "." in name else "jpg"
    data, ext = result
    return ContentFile(data), ext


def commit_photo(instance, field_name: str, filename: str, body: ContentFile) -> None:
    field = getattr(instance, field_name)
    old_name = field.name if field else ""
    field.save(filename, body, save=False)
    instance.photo_updated_at = timezone.now()
    instance.save(update_fields=[field_name, "photo_updated_at"])
    if old_name and old_name != field.name:
        field.storage.delete(old_name)


def _as_rgb(im: Image.Image) -> Image.Image:
    if im.mode == "RGB":
        return im
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return im.convert("RGB")
