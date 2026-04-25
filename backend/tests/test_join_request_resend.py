"""Tests for the resend-magic-link endpoint on approved join requests."""

import pytest
from community._validation import Code
from community.models import JoinRequestStatus

from tests._asserts import assert_error_code


def _approve(api_client, vettor_headers, join_request):
    return api_client.patch(
        f"/api/community/join-requests/{join_request.id}/",
        {"status": JoinRequestStatus.APPROVED},
        content_type="application/json",
        **vettor_headers,
    )


@pytest.mark.django_db
class TestResendMagicLink:
    def test_success_for_approved_user_who_has_not_logged_in(
        self, api_client, vettor_headers, sample_join_request
    ):
        approve_response = _approve(api_client, vettor_headers, sample_join_request)
        original_token = approve_response.json()["magic_link_token"]

        response = api_client.post(
            f"/api/community/join-requests/{sample_join_request.id}/resend-magic-link/",
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["magic_link_token"] is not None
        assert body["magic_link_token"] != original_token
        assert body["status"] == JoinRequestStatus.APPROVED

    def test_resend_invalidates_previous_unused_tokens(
        self, api_client, vettor_headers, sample_join_request
    ):
        from users.models import MagicLoginToken, User

        approve_response = _approve(api_client, vettor_headers, sample_join_request)
        original_token = approve_response.json()["magic_link_token"]

        response = api_client.post(
            f"/api/community/join-requests/{sample_join_request.id}/resend-magic-link/",
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        new_token = response.json()["magic_link_token"]

        user = User.objects.get(phone_number=sample_join_request.phone_number)
        assert MagicLoginToken.objects.get(user=user, token=original_token).used is True
        assert MagicLoginToken.objects.get(user=user, token=new_token).used is False

        # The old token should now be rejected by the magic-login endpoint.
        old_login = api_client.get(f"/api/auth/magic-login/{original_token}/")
        assert old_login.status_code == 400

    def test_pending_request_rejected(self, api_client, vettor_headers, sample_join_request):
        response = api_client.post(
            f"/api/community/join-requests/{sample_join_request.id}/resend-magic-link/",
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.JoinRequest.NOT_APPROVED)

    def test_already_logged_in_user_rejected(self, api_client, vettor_headers, sample_join_request):
        from users.models import User

        _approve(api_client, vettor_headers, sample_join_request)
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        user.needs_onboarding = False
        user.save(update_fields=["needs_onboarding"])

        response = api_client.post(
            f"/api/community/join-requests/{sample_join_request.id}/resend-magic-link/",
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.JoinRequest.ALREADY_LOGGED_IN)

    def test_archived_user_rejected(self, api_client, vettor_headers, sample_join_request):
        from django.utils import timezone
        from users.models import User

        _approve(api_client, vettor_headers, sample_join_request)
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        user.archived_at = timezone.now()
        user.save(update_fields=["archived_at"])

        response = api_client.post(
            f"/api/community/join-requests/{sample_join_request.id}/resend-magic-link/",
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 403
        assert_error_code(response, Code.Auth.ACCOUNT_ARCHIVED)

    def test_paused_user_rejected(self, api_client, vettor_headers, sample_join_request):
        from users.models import User

        _approve(api_client, vettor_headers, sample_join_request)
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        user.is_paused = True
        user.save(update_fields=["is_paused"])

        response = api_client.post(
            f"/api/community/join-requests/{sample_join_request.id}/resend-magic-link/",
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 403
        assert_error_code(response, Code.Auth.ACCOUNT_PAUSED)

    def test_not_found(self, api_client, vettor_headers):
        import uuid

        response = api_client.post(
            f"/api/community/join-requests/{uuid.uuid4()}/resend-magic-link/",
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 404
        assert_error_code(response, Code.JoinRequest.NOT_FOUND)

    def test_requires_permission(self, api_client, auth_headers, sample_join_request):
        response = api_client.post(
            f"/api/community/join-requests/{sample_join_request.id}/resend-magic-link/",
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_unauthenticated(self, api_client, sample_join_request):
        response = api_client.post(
            f"/api/community/join-requests/{sample_join_request.id}/resend-magic-link/",
            content_type="application/json",
        )
        assert response.status_code == 401
