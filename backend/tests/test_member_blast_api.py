from unittest.mock import patch

import pytest
from audit.models import AuditLogEntry
from community.validation import Code
from notifications.email_types import BatchSendResult
from notifications.models import MemberEmailBlast
from users.models import MembershipStatus
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._users import make_user

URL = "/api/notifications/email-blasts/"
BODY = {"subject": "hello", "body_html": "<p>hi</p>"}

pytestmark = pytest.mark.django_db


@pytest.fixture
def sender():
    with patch("notifications.member_blasts.service.get_email_sender") as get:
        get.return_value.send_batch.return_value = BatchSendResult(accepted=2)
        yield get.return_value.send_batch


@pytest.fixture
def admin():
    return make_user(
        PermissionKey.SEND_EMAIL_BLAST, membership_status=MembershipStatus.ACTIVE_MEMBER
    )


@pytest.fixture
def headers(admin):
    return auth_headers_for(admin)


def test_all_routes_403_without_permission(api_client):
    headers = auth_headers_for(make_user())
    calls = [
        api_client.post(URL + "preview/", BODY, content_type="application/json", **headers),
        api_client.post(URL + "test/", BODY, content_type="application/json", **headers),
        api_client.post(URL, BODY, content_type="application/json", **headers),
        api_client.get(URL, **headers),
    ]
    for response in calls:
        assert_error_code(response, Code.Perm.DENIED)
        assert response.status_code == 403


def test_preview_returns_counts_and_sanitized_html(api_client, headers):
    make_user(membership_status=MembershipStatus.ACTIVE_MEMBER)
    body = {"subject": "s", "body_html": '<p onclick="x">hi</p>'}
    response = api_client.post(URL + "preview/", body, content_type="application/json", **headers)
    data = response.json()
    assert "onclick" not in data["html"]
    assert data["recipient_count"] == 2


def test_send_test_reports_sent(api_client, headers, sender):
    response = api_client.post(URL + "test/", BODY, content_type="application/json", **headers)
    assert response.json() == {"sent": True}


def test_send_returns_counts_and_audits(
    api_client, admin, headers, sender, django_capture_on_commit_callbacks
):
    make_user(membership_status=MembershipStatus.ACTIVE_MEMBER)
    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(URL, BODY, content_type="application/json", **headers)
    data = response.json()
    assert data["status"] == "sent"
    assert data["sender_id"] == str(admin.pk)
    assert AuditLogEntry.objects.filter(action="member_email_blast_sent").exists()


def test_send_duplicate_returns_400_code(api_client, headers, sender):
    api_client.post(URL, BODY, content_type="application/json", **headers)
    response = api_client.post(URL, BODY, content_type="application/json", **headers)
    assert_error_code(response, Code.Notification.BLAST_DUPLICATE)


def test_send_audits_unknown_blast_when_provider_raises(
    api_client, headers, sender, django_capture_on_commit_callbacks
):
    sender.side_effect = RuntimeError("provider down")
    with django_capture_on_commit_callbacks(execute=True), pytest.raises(RuntimeError):
        api_client.post(URL, BODY, content_type="application/json", **headers)
    entry = AuditLogEntry.objects.get(action="member_email_blast_sent")
    assert entry.details["status"] == "unknown"


def test_list_returns_recent_blasts_newest_first(api_client, admin, headers):
    for s in ("first", "second"):
        MemberEmailBlast.objects.create(sender=admin, subject=s, body_html="x", recipient_count=5)
    response = api_client.get(URL, **headers)
    assert [b["subject"] for b in response.json()] == ["second", "first"]
    assert response.json()[0]["sent_count"] == 0
