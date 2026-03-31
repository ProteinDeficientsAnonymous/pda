"""Tests for profile and event photo upload/delete endpoints."""

import io

import pytest
from community.models import Event
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role


def _make_test_image(fmt="JPEG", size=(20, 20)):
    buf = io.BytesIO()
    Image.new("RGB", size).save(buf, format=fmt)
    buf.seek(0)
    ct = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
    return SimpleUploadedFile(
        f"test.{fmt.lower()}", buf.read(), content_type=ct.get(fmt, "image/jpeg")
    )


def _auth(user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}


@pytest.fixture
def member(db):
    return User.objects.create_user(
        phone_number="+12025550201",
        password="testpass123",
        display_name="Photo Tester",
    )


@pytest.fixture
def manager(db):
    role = Role.objects.create(name="event_manager", permissions=[PermissionKey.MANAGE_EVENTS])
    user = User.objects.create_user(
        phone_number="+12025550202",
        password="testpass123",
        display_name="Manager",
    )
    user.roles.add(role)
    return user


@pytest.fixture
def event(db, member):
    return Event.objects.create(
        title="Test Event",
        start_datetime="2026-06-01T18:00:00Z",
        created_by=member,
    )


# ---------------------------------------------------------------------------
# Profile photo tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProfilePhoto:
    def test_upload_photo(self, api_client, member):
        photo = _make_test_image()
        response = api_client.post(
            "/api/auth/me/photo/",
            {"photo": photo},
            **_auth(member),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["profile_photo_url"] != ""
        member.refresh_from_db()
        assert member.profile_photo

    def test_upload_replaces_existing(self, api_client, member):
        photo1 = _make_test_image()
        api_client.post("/api/auth/me/photo/", {"photo": photo1}, **_auth(member))
        photo2 = _make_test_image("PNG")
        response = api_client.post("/api/auth/me/photo/", {"photo": photo2}, **_auth(member))
        assert response.status_code == 200
        member.refresh_from_db()
        assert ".png" in member.profile_photo.name

    def test_upload_rejects_non_image(self, api_client, member):
        fake = SimpleUploadedFile("test.txt", b"not an image", content_type="text/plain")
        response = api_client.post("/api/auth/me/photo/", {"photo": fake}, **_auth(member))
        assert response.status_code == 400

    def test_upload_rejects_too_large(self, api_client, member):
        buf = io.BytesIO(b"\x00" * (6 * 1024 * 1024))
        big = SimpleUploadedFile("big.jpg", buf.read(), content_type="image/jpeg")
        response = api_client.post("/api/auth/me/photo/", {"photo": big}, **_auth(member))
        assert response.status_code == 400

    def test_delete_photo(self, api_client, member):
        photo = _make_test_image()
        api_client.post("/api/auth/me/photo/", {"photo": photo}, **_auth(member))
        response = api_client.delete("/api/auth/me/photo/", **_auth(member))
        assert response.status_code == 200
        assert response.json()["profile_photo_url"] == ""
        member.refresh_from_db()
        assert not member.profile_photo

    def test_upload_requires_auth(self, api_client):
        photo = _make_test_image()
        response = api_client.post("/api/auth/me/photo/", {"photo": photo})
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Event photo tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEventPhoto:
    def test_creator_can_upload(self, api_client, member, event):
        photo = _make_test_image()
        response = api_client.post(
            f"/api/community/events/{event.id}/photo/",
            {"photo": photo},
            **_auth(member),
        )
        assert response.status_code == 200
        assert response.json()["photo_url"] != ""

    def test_manager_can_upload(self, api_client, manager, event):
        photo = _make_test_image()
        response = api_client.post(
            f"/api/community/events/{event.id}/photo/",
            {"photo": photo},
            **_auth(manager),
        )
        assert response.status_code == 200

    def test_non_creator_non_manager_rejected(self, api_client, event):
        other = User.objects.create_user(
            phone_number="+12025550203",
            password="testpass123",
            display_name="Rando",
        )
        photo = _make_test_image()
        response = api_client.post(
            f"/api/community/events/{event.id}/photo/",
            {"photo": photo},
            **_auth(other),
        )
        assert response.status_code == 403

    def test_upload_rejects_non_image(self, api_client, member, event):
        fake = SimpleUploadedFile("test.txt", b"not an image", content_type="text/plain")
        response = api_client.post(
            f"/api/community/events/{event.id}/photo/",
            {"photo": fake},
            **_auth(member),
        )
        assert response.status_code == 400

    def test_upload_rejects_too_large(self, api_client, member, event):
        buf = io.BytesIO(b"\x00" * (11 * 1024 * 1024))
        big = SimpleUploadedFile("big.jpg", buf.read(), content_type="image/jpeg")
        response = api_client.post(
            f"/api/community/events/{event.id}/photo/",
            {"photo": big},
            **_auth(member),
        )
        assert response.status_code == 400

    def test_delete_photo(self, api_client, member, event):
        photo = _make_test_image()
        api_client.post(
            f"/api/community/events/{event.id}/photo/",
            {"photo": photo},
            **_auth(member),
        )
        response = api_client.delete(
            f"/api/community/events/{event.id}/photo/",
            **_auth(member),
        )
        assert response.status_code == 200
        assert response.json()["photo_url"] == ""

    def test_photo_url_in_event_detail(self, api_client, member, event):
        photo = _make_test_image()
        api_client.post(
            f"/api/community/events/{event.id}/photo/",
            {"photo": photo},
            **_auth(member),
        )
        response = api_client.get(
            f"/api/community/events/{event.id}/",
            **_auth(member),
        )
        assert response.status_code == 200
        assert response.json()["photo_url"] != ""

    def test_event_not_found(self, api_client, member):
        photo = _make_test_image()
        response = api_client.post(
            "/api/community/events/00000000-0000-0000-0000-000000000000/photo/",
            {"photo": photo},
            **_auth(member),
        )
        assert response.status_code == 404
