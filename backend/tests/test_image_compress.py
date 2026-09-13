import io
import os

import pytest
from community._image_compress import (
    AVATAR_MAX_EDGE,
    EVENT_MAX_EDGE,
    UnsafeImageError,
    compress_photo,
)
from PIL import Image, ImageSequence


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


def _animated_webp(
    *, frames: int = 4, size: tuple[int, int] = (32, 32), quality: int = 80
) -> bytes:
    images = [Image.new("RGBA", size, (i * 40, 10, 200, 255)) for i in range(frames)]
    buf = io.BytesIO()
    images[0].save(
        buf,
        format="WEBP",
        save_all=True,
        append_images=images[1:],
        duration=80,
        loop=0,
        quality=quality,
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
        result = compress_photo(raw, max_edge=EVENT_MAX_EDGE)
        assert result is not None
        data, ext = result
        assert ext == "jpg"
        with Image.open(io.BytesIO(data)) as im:
            assert im.size == (EVENT_MAX_EDGE, EVENT_MAX_EDGE * 900 // 1600)

    def test_oversized_still_is_resized_to_avatar_max_edge(self):
        raw = _noisy_png((800, 600))
        result = compress_photo(raw, AVATAR_MAX_EDGE)
        assert result is not None
        data, ext = result
        assert ext == "jpg"
        with Image.open(io.BytesIO(data)) as im:
            assert im.size == (AVATAR_MAX_EDGE, AVATAR_MAX_EDGE * 600 // 800)

    def test_exif_orientation_is_baked_in_before_resize(self):
        # Stored 1600×900 + Orientation=6 (90° CW) displays as 900×1600.
        # JPEG save strips EXIF, so we must rotate pixels first or the
        # photo comes out sideways after compress (Leah's #1291 follow-up).
        im = Image.frombytes("RGB", (1600, 900), os.urandom(1600 * 900 * 3))
        exif = im.getexif()
        exif[0x0112] = 6
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=95, exif=exif)
        result = compress_photo(buf.getvalue(), EVENT_MAX_EDGE)
        assert result is not None
        data, ext = result
        assert ext == "jpg"
        with Image.open(io.BytesIO(data)) as out:
            assert out.size == (EVENT_MAX_EDGE * 900 // 1600, EVENT_MAX_EDGE)
            assert not out.getexif().get(0x0112)

    def test_tiny_png_returns_none_when_jpeg_is_not_smaller(self):
        assert compress_photo(_png_bytes(), EVENT_MAX_EDGE) is None

    def test_animated_webp_returns_none_when_reencode_is_not_smaller(self, monkeypatch):
        raw = _animated_webp(frames=4)
        orig_save = Image.Image.save

        def fat_webp_save(self, fp, format=None, **kwargs):
            if format == "WEBP":
                fp.write(b"\x00" * (len(raw) + 1))
                return
            return orig_save(self, fp, format=format, **kwargs)

        monkeypatch.setattr(Image.Image, "save", fat_webp_save)
        assert compress_photo(raw, EVENT_MAX_EDGE) is None

    def test_fat_animated_webp_is_reencoded(self):
        raw = _animated_webp(frames=8, size=(96, 96), quality=100)
        result = compress_photo(raw, EVENT_MAX_EDGE)
        assert result is not None
        data, ext = result
        assert ext == "webp"
        assert len(data) < len(raw)
        with Image.open(io.BytesIO(data)) as im:
            assert im.format == "WEBP"
            assert im.n_frames == 8

    def test_animated_gif_total_pixels_over_limit_raises(self, monkeypatch):
        raw = _gif_bytes(frames=12, size=(96, 96))
        monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 96 * 96 * 3)
        with pytest.raises(UnsafeImageError):
            compress_photo(raw, EVENT_MAX_EDGE)

    def test_memory_error_during_gif_decode_raises(self, monkeypatch):
        raw = _gif_bytes(frames=12)

        def boom(*_args, **_kwargs):
            raise MemoryError

        monkeypatch.setattr(ImageSequence, "Iterator", boom)
        with pytest.raises(UnsafeImageError):
            compress_photo(raw, EVENT_MAX_EDGE)

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
