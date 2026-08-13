from types import SimpleNamespace

from config.media_proxy import media_path
from config.og_preview import _absolute
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage


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
