import io
import os
from io import StringIO

import pytest
from community.models import Event
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from PIL import Image
from users.models import User

from tests.conftest import future_iso


def _noisy_png(size=(240, 240)) -> bytes:
    buf = io.BytesIO()
    Image.frombytes("RGB", size, os.urandom(size[0] * size[1] * 3)).save(buf, format="PNG")
    return buf.getvalue()


def _run(*args) -> str:
    out = StringIO()
    call_command("compress_existing_photos", *args, stdout=out)
    return out.getvalue()


@pytest.fixture
def member(db):
    return User.objects.create_user(
        phone_number="+12025550901",
        password="testpass123",
        first_name="Backfill",
    )


@pytest.fixture
def event(db, member):
    ev = Event.objects.create(
        title="Compress Me",
        start_datetime=future_iso(days=10),
        created_by=member,
    )
    ev.photo.save("original.png", ContentFile(_noisy_png()), save=True)
    return ev


@pytest.mark.django_db
class TestCompressExistingPhotos:
    def test_dry_run_keeps_original_file_and_name(self, event):
        old = event.photo.name
        out = _run()
        event.refresh_from_db()
        assert event.photo.name == old
        assert default_storage.exists(old)
        assert "would write 1" in out

    def test_commit_writes_new_file_and_keeps_original(self, event):
        old = event.photo.name
        out = _run("--commit")
        event.refresh_from_db()
        assert event.photo.name != old
        assert event.photo.name.endswith(".jpg")
        assert default_storage.exists(old)
        assert default_storage.exists(event.photo.name)
        assert f"keep {old}" in out

    def test_commit_keeps_original_avatar(self, member):
        member.profile_photo.save("avatar.png", ContentFile(_noisy_png()), save=True)
        old = member.profile_photo.name
        _run("--commit")
        member.refresh_from_db()
        assert member.profile_photo.name != old
        assert default_storage.exists(old)
        assert default_storage.exists(member.profile_photo.name)
        assert member.photo_updated_at is not None

    def test_skips_unreadable_photo_and_continues(self, event, member):
        event.photo.name = "missing.png"
        event.save(update_fields=["photo"])
        member.profile_photo.save("avatar.png", ContentFile(_noisy_png()), save=True)
        out = StringIO()
        err = StringIO()
        call_command("compress_existing_photos", "--commit", stdout=out, stderr=err)
        member.refresh_from_db()
        assert member.profile_photo.name.endswith(".jpg")
        combined = out.getvalue() + err.getvalue()
        assert "skip" in combined

    def test_help_says_originals_stay_in_storage(self):
        from community.management.commands.compress_existing_photos import Command

        help_text = Command.help.lower()
        assert "originals stay" in help_text
        assert "dry-run" in help_text
        assert "skipped" in help_text
