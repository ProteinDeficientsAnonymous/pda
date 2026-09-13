import io

from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageOps, ImageSequence

EVENT_MAX_EDGE = 1200
AVATAR_MAX_EDGE = 512
# JPEG/WebP quality 1–100; same as frontend JPEG_QUALITY 0.8.
_QUALITY = 80
# Pillow WebP: 0=fast/large … 6=slow/small. 4 is the encoder default.
_WEBP_METHOD = 4
# GIF spec stores delay in 10ms units; 0 means “use the viewer default”.
_GIF_FRAME_MS = 100
_GIF_LOOP_FOREVER = 0
_JPEG_BACKGROUND = (255, 255, 255)
_ANIM_FORMATS = frozenset({"GIF", "WEBP"})


class UnsafeImageError(Exception):
    """Pixel or RAM bomb — callers must 400, not store the original."""


def _too_many_pixels(im: Image.Image) -> bool:
    # Pillow's bomb check is per frame. A 200-frame GIF can still fill RAM.
    limit = Image.MAX_IMAGE_PIXELS
    return bool(limit) and im.size[0] * im.size[1] * getattr(im, "n_frames", 1) > limit


def _anim_to_webp(data: bytes) -> bytes | None:
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.format not in _ANIM_FORMATS or getattr(im, "n_frames", 1) <= 1:
                return None
            if _too_many_pixels(im):
                raise UnsafeImageError
            frames, durations = zip(
                *[
                    (frame.convert("RGBA"), frame.info.get("duration", _GIF_FRAME_MS))
                    for frame in ImageSequence.Iterator(im)
                ]
            )
            loop = im.info.get("loop", _GIF_LOOP_FOREVER)
        buf = io.BytesIO()
        frames[0].save(
            buf,
            format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=loop,
            quality=_QUALITY,
            method=_WEBP_METHOD,
        )
        webp = buf.getvalue()
    except (MemoryError, Image.DecompressionBombError):
        raise UnsafeImageError from None
    except OSError:
        return None
    if len(webp) >= len(data):
        return None
    return webp


def _still_to_jpeg(data: bytes, max_edge: int) -> bytes | None:
    try:
        with Image.open(io.BytesIO(data)) as im:
            if getattr(im, "n_frames", 1) > 1:
                return None
            if _too_many_pixels(im):
                raise UnsafeImageError
            rgb = _as_rgb(ImageOps.exif_transpose(im))
            rgb.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            rgb.save(buf, format="JPEG", quality=_QUALITY, optimize=True)
        jpeg = buf.getvalue()
    except (MemoryError, Image.DecompressionBombError):
        raise UnsafeImageError from None
    except OSError:
        return None
    if len(jpeg) >= len(data):
        return None
    return jpeg


def compress_photo(data: bytes, max_edge: int) -> tuple[bytes, str] | None:
    webp = _anim_to_webp(data)
    if webp is not None:
        return webp, "webp"
    jpeg = _still_to_jpeg(data, max_edge)
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
        bg = Image.new("RGB", rgba.size, _JPEG_BACKGROUND)
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return im.convert("RGB")
