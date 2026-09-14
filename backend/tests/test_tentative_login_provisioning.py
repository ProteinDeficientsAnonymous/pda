"""Tentative approval provisions a login the same way full approval does.

The applicant gets a magic token and lands in onboarding; what differs is the
access they end up with (see test_tentative_member_access.py), not the path in.
"""

import pytest
from community.models import JoinRequestStatus
from django.utils import timezone
from users.models import MagicLoginToken

pytestmark = pytest.mark.django_db


def _tentatively_approve(api_client, vettor_headers, join_request):
    return api_client.patch(
        f"/api/community/join-requests/{join_request.id}/",
        {"status": JoinRequestStatus.TENTATIVE},
        content_type="application/json",
        **vettor_headers,
    )


def test_tentative_returns_a_magic_link_token(api_client, vettor_headers, sample_join_request):
    response = _tentatively_approve(api_client, vettor_headers, sample_join_request)
    assert response.status_code == 200
    token = response.json()["magic_link_token"]
    assert token
    sample_join_request.refresh_from_db()
    assert MagicLoginToken.objects.filter(
        token=token, user=sample_join_request.user, used=False
    ).exists()


def test_tentative_user_needs_onboarding(api_client, vettor_headers, sample_join_request):
    _tentatively_approve(api_client, vettor_headers, sample_join_request)
    sample_join_request.refresh_from_db()
    assert sample_join_request.user.needs_onboarding is True
    assert sample_join_request.user.is_member is False


def test_tentative_still_returns_the_rsvp_link_token(
    api_client, vettor_headers, sample_join_request
):
    response = _tentatively_approve(api_client, vettor_headers, sample_join_request)
    assert response.json()["rsvp_link_token"]


def test_tentative_still_sends_no_email(
    api_client, vettor_headers, sample_join_request, fake_email_sender
):
    _tentatively_approve(api_client, vettor_headers, sample_join_request)
    fake_email_sender.send.assert_not_called()


def test_magic_token_logs_the_tentative_user_in(api_client, vettor_headers, sample_join_request):
    token = _tentatively_approve(api_client, vettor_headers, sample_join_request).json()[
        "magic_link_token"
    ]
    response = api_client.get(f"/api/auth/magic-login/{token}/")
    assert response.status_code == 200
    assert response.json()["access"]


def test_tentative_carries_the_form_consents(api_client, vettor_headers, sample_join_request):
    sample_join_request.guidelines_consent_at = timezone.now()
    sample_join_request.sms_consent_at = timezone.now()
    sample_join_request.save(update_fields=["guidelines_consent_at", "sms_consent_at"])
    _tentatively_approve(api_client, vettor_headers, sample_join_request)
    sample_join_request.refresh_from_db()
    assert sample_join_request.user.guidelines_consent_at is not None
    assert sample_join_request.user.sms_consent_at is not None
