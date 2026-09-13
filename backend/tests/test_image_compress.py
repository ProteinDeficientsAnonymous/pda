import io
import os

import pytest
from community._image_compress import EVENT_MAX_EDGE, compress_photo
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


def _noisy_png(size: tuple[int, int] = (240, 240)) -> bytes:
    buf = io.BytesIO()
    Image.frombytes("RGB", size, os.urandom(size[0] * size[1] * 3)).save(buf, format="PNG")
    return buf.getvalue()


def _animated_webp(*, frames: int = 4) -> bytes:
    images = [Image.new("RGBA", (32, 32), (i * 40, 10, 200, 255)) for i in range(frames)]
    buf = io.BytesIO()
    images[0].save(
        buf,
        format="WEBP",
        save_all=True,
        append_images=images[1:],
        duration=80,
        loop=0,
    )
    return buf.getvalue()


@pytest.mark.unit
class TestCompressPhoto:
    def test_noisy_png_becomes_smaller_jpeg(self):
        raw = _noisy_png()
        result = compress_photo(raw, EVENT_MAX_EDGE)
        assert result is not None
        data, ext = result
        assert ext == "jpg"
        assert len(data) < len(raw)
        with Image.open(io.BytesIO(data)) as im:
            assert im.format == "JPEG"

    def test_oversized_still_is_resized_to_max_edge(self):
        raw = _noisy_png((1600, 900))
        result = compress_photo(raw, max_edge=1200)
        assert result is not None
        data, ext = result
        assert ext == "jpg"
        with Image.open(io.BytesIO(data)) as im:
            assert im.size == (1200, 675)

    def test_tiny_png_returns_none_when_jpeg_is_not_smaller(self):
        assert compress_photo(_png_bytes(), EVENT_MAX_EDGE) is None

    def test_animated_webp_is_left_alone(self):
        assert compress_photo(_animated_webp(), EVENT_MAX_EDGE) is None

    def test_garbage_bytes_return_none(self):
        assert compress_photo(b"not-an-image", EVENT_MAX_EDGE) is None

    def test_animated_gif_returns_none_when_webp_is_not_smaller(self, monkeypatch):
        raw = _gif_bytes(frames=2, size=(4, 4))
        orig_save = Image.Image.save

        def fat_webp_save(self, fp, format=None, **kwargs):
            if format == "WEBP":
                fp.write(b"\x00" * (len(raw) + 1))
                return
            return orig_save(self, fp, format=format, **kwargs)

        monkeypatch.setattr(Image.Image, "save", fat_webp_save)
        assert compress_photo(raw, EVENT_MAX_EDGE) is None

    def test_animated_gif_returns_webp(self):
        result = compress_photo(_gif_bytes(frames=12), EVENT_MAX_EDGE)
        assert result is not None
        data, ext = result
        assert ext == "webp"
        with Image.open(io.BytesIO(data)) as im:
            assert im.format == "WEBP"
            assert im.n_frames == 12
