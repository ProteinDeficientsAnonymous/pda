import io

from django.core.files.base import ContentFile
from PIL import Image, ImageSequence, UnidentifiedImageError

EVENT_MAX_EDGE = 1200
AVATAR_MAX_EDGE = 512
_JPEG_QUALITY = 80
_WEBP_QUALITY = 80


def maybe_webp_from_animated_gif(data: bytes) -> bytes | None:
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
        quality=_WEBP_QUALITY,
        method=4,
    )
    webp = buf.getvalue()
    if len(webp) >= len(data):
        return None
    return webp


def maybe_jpeg_from_still(data: bytes, max_edge: int) -> bytes | None:
    try:
        im = Image.open(io.BytesIO(data))
    except UnidentifiedImageError:
        return None
    with im:
        if im.format == "GIF" and getattr(im, "n_frames", 1) > 1:
            return None
        rgb = _as_rgb(im)
        longer = max(rgb.size)
        if longer > max_edge:
            scale = max_edge / longer
            rgb = rgb.resize(
                (round(rgb.size[0] * scale), round(rgb.size[1] * scale)),
                Image.Resampling.LANCZOS,
            )
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
    jpeg = buf.getvalue()
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
        return ContentFile(raw), _fallback_ext(name)
    data, ext = result
    return ContentFile(data), ext


def _fallback_ext(name: str) -> str:
    return name.rsplit(".", 1)[-1] if "." in name else "jpg"


def _as_rgb(im: Image.Image) -> Image.Image:
    if im.mode == "RGB":
        return im
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return im.convert("RGB")
