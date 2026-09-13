import io

import pytest
from community._image_compress import maybe_webp_from_animated_gif
from PIL import Image


def _gif_bytes(*, frames: int, size: tuple[int, int] = (96, 96)) -> bytes:
    images = [Image.new("RGB", size, (i * 17 % 255, 40, 200 - i * 3)) for i in range(frames)]
    buf = io.BytesIO()
    images[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=images[1:],
        duration=80,
        loop=0,
    )
    return buf.getvalue()


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.unit
class TestMaybeWebpFromAnimatedGif:
    def test_animated_gif_returns_webp_with_same_frame_count(self):
        raw = _gif_bytes(frames=12)
        webp = maybe_webp_from_animated_gif(raw)
        assert webp is not None
        with Image.open(io.BytesIO(webp)) as im:
            assert im.format == "WEBP"
            assert im.n_frames == 12

    def test_still_png_returns_none(self):
        assert maybe_webp_from_animated_gif(_png_bytes()) is None

    def test_single_frame_gif_returns_none(self):
        assert maybe_webp_from_animated_gif(_gif_bytes(frames=1)) is None
