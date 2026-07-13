import io
import uuid

import pytest
from community.models import Event, EventStatus, PageVisibility
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from tests.conftest import future_iso


def _make_test_image():
    buf = io.BytesIO()
    Image.new("RGB", (20, 20)).save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile("test.jpg", buf.read(), content_type="image/jpeg")


def _preview_url(event_id) -> str:
    return f"/events/{event_id}/preview/"


@pytest.fixture
def public_event(db):
    return Event.objects.create(
        title="Vegan Potluck",
        description="Bring a dish to share at the park.",
        start_datetime=future_iso(),
        location="Central Park",
        visibility=PageVisibility.PUBLIC,
        status=EventStatus.ACTIVE,
        photo=_make_test_image(),
    )


@pytest.mark.django_db
class TestEventOgPreview:
    def test_public_event_renders_og_tags(self, api_client, public_event, settings):
        settings.FRONTEND_BASE_URL = "https://pda.example.com"
        response = api_client.get(_preview_url(public_event.id))

        assert response.status_code == 200
        html = response.content.decode()
        assert '<meta property="og:title" content="Vegan Potluck"' in html
        assert (
            '<meta property="og:description" content="Bring a dish to share at the park."' in html
        )
        assert (
            f'<meta property="og:url" content="https://pda.example.com/events/{public_event.id}"'
            in html
        )
        assert (
            '<meta property="og:image" content="https://pda.example.com/media/event_photos/' in html
        )
        assert '<meta name="twitter:card" content="summary_large_image"' in html

    def test_event_without_photo_uses_summary_card(self, api_client, db, settings):
        settings.FRONTEND_BASE_URL = "https://pda.example.com"
        event = Event.objects.create(
            title="No Photo Event",
            start_datetime=future_iso(),
            visibility=PageVisibility.PUBLIC,
            status=EventStatus.ACTIVE,
        )
        response = api_client.get(_preview_url(event.id))

        assert response.status_code == 200
        html = response.content.decode()
        assert '<meta name="twitter:card" content="summary"' in html
        assert "og:image" not in html

    def test_members_only_event_is_hidden(self, api_client, db):
        event = Event.objects.create(
            title="Secret Members Event",
            start_datetime=future_iso(),
            visibility=PageVisibility.MEMBERS_ONLY,
            status=EventStatus.ACTIVE,
        )
        response = api_client.get(_preview_url(event.id))
        assert response.status_code == 404

    def test_invite_only_event_is_hidden(self, api_client, db):
        event = Event.objects.create(
            title="Invite Only Event",
            start_datetime=future_iso(),
            visibility=PageVisibility.INVITE_ONLY,
            status=EventStatus.ACTIVE,
        )
        response = api_client.get(_preview_url(event.id))
        assert response.status_code == 404

    def test_cancelled_public_event_still_previews(self, api_client, db, settings):
        settings.FRONTEND_BASE_URL = "https://pda.example.com"
        event = Event.objects.create(
            title="Cancelled Event",
            start_datetime=future_iso(),
            visibility=PageVisibility.PUBLIC,
            status=EventStatus.CANCELLED,
        )
        response = api_client.get(_preview_url(event.id))

        assert response.status_code == 200
        assert '<meta property="og:title" content="Cancelled Event"' in response.content.decode()

    def test_draft_event_is_hidden(self, api_client, db):
        event = Event.objects.create(
            title="Draft Event",
            start_datetime=future_iso(),
            visibility=PageVisibility.PUBLIC,
            status=EventStatus.DRAFT,
        )
        response = api_client.get(_preview_url(event.id))
        assert response.status_code == 404

    def test_missing_event_returns_404(self, api_client, db):
        response = api_client.get(_preview_url(uuid.uuid4()))
        assert response.status_code == 404

    def test_description_is_truncated(self, api_client, db, settings):
        settings.FRONTEND_BASE_URL = "https://pda.example.com"
        event = Event.objects.create(
            title="Long Description Event",
            description="word " * 100,
            start_datetime=future_iso(),
            visibility=PageVisibility.PUBLIC,
            status=EventStatus.ACTIVE,
        )
        response = api_client.get(_preview_url(event.id))

        html = response.content.decode()
        assert "…" in html

    def test_title_is_html_escaped(self, api_client, db, settings):
        settings.FRONTEND_BASE_URL = "https://pda.example.com"
        event = Event.objects.create(
            title='Evil "><script>alert(1)</script>',
            start_datetime=future_iso(),
            visibility=PageVisibility.PUBLIC,
            status=EventStatus.ACTIVE,
        )
        response = api_client.get(_preview_url(event.id))

        html = response.content.decode()
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html
