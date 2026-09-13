from types import SimpleNamespace

import pytest
from config.media_proxy import SIGNED_URL_CACHE_TTL, media_path
from config.og_preview import _absolute
from django.core.cache import caches
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage


class _CountingUrlField:
    def __init__(self, name="profile_photos/u1.jpg", updated_at="2026-01-01T00:00:00Z"):
        self.name = name
        self.instance = SimpleNamespace(photo_updated_at=updated_at)
        self.calls = 0

    @property
    def url(self):
        self.calls += 1
        return f"https://s3.example/{self.name}?sig={self.calls}"


@pytest.fixture(autouse=True)
def _clear_media_url_cache():
    caches["media"].clear()


@pytest.mark.unit
class TestMediaPath:
    def test_empty_field_returns_empty_string(self):
        assert media_path(None) == ""
        assert media_path("") == ""

    def test_uses_storage_url(self):
        field = SimpleNamespace(url="https://s3.example/bucket/photo.jpg?X-Amz-Signature=abc")
        assert media_path(field) == "https://s3.example/bucket/photo.jpg?X-Amz-Signature=abc"

    def test_filesystem_storage_stays_relative(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        settings.MEDIA_URL = "/media/"
        storage = FileSystemStorage(location=str(tmp_path), base_url="/media/")
        name = storage.save("profile_photos/a.jpg", ContentFile(b"fake"))
        field = SimpleNamespace(url=storage.url(name))

        assert media_path(field) == f"/media/{name}"

    def test_reuses_signed_url_for_same_object(self):
        field = _CountingUrlField()
        first = media_path(field)
        second = media_path(field)
        assert first == second
        assert field.calls == 1
        assert first == "https://s3.example/profile_photos/u1.jpg?sig=1"

    def test_mints_new_signed_url_when_photo_updated_at_changes(self):
        field = _CountingUrlField(updated_at="2026-01-01T00:00:00Z")
        first = media_path(field)
        field.instance.photo_updated_at = "2026-06-01T00:00:00Z"
        second = media_path(field)
        assert first != second
        assert field.calls == 2

    def test_does_not_cache_relative_media_urls(self):
        field = SimpleNamespace(name="profile_photos/a.jpg", url="/media/profile_photos/a.jpg")
        assert media_path(field) == "/media/profile_photos/a.jpg"

    def test_signed_url_cache_ttl_leaves_one_day_before_signature_expires(self):
        assert SIGNED_URL_CACHE_TTL == 60 * 60 * 24 * 6

    def test_mints_fresh_signature_when_cache_entry_is_gone(self):
        field = _CountingUrlField()
        first = media_path(field)
        caches["media"].clear()
        second = media_path(field)
        assert first != second
        assert field.calls == 2
        assert second.endswith("sig=2")


class TestOgAbsolute:
    def test_prefixes_relative_media_path(self, settings):
        settings.FRONTEND_BASE_URL = "https://pda.example.com"
        assert (
            _absolute("/media/event_photos/a.jpg")
            == "https://pda.example.com/media/event_photos/a.jpg"
        )

    def test_passes_through_absolute_https_url(self, settings):
        settings.FRONTEND_BASE_URL = "https://pda.example.com"
        signed = "https://s3.us-west.example/bucket/event_photos/a.jpg?X-Amz-Signature=abc"
        assert _absolute(signed) == signed

    def test_empty_returns_empty(self, settings):
        settings.FRONTEND_BASE_URL = "https://pda.example.com"
        assert _absolute("") == ""
