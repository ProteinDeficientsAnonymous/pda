import io

from PIL import Image, ImageSequence

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
