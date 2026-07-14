"""Tests for join request phone/email conflicts and archived re-use.

A submission collides with an active member when the phone or (non-archived)
email already belongs to one — surfaced as ALREADY_MEMBER. Non-member matches
attach instead (see test_join_request_integration.py). Archived accounts are
ignored so a former member can re-join with the same phone/email. `why_join_id`
and the rate-limit cache reset come from conftest.
"""

import pytest
from community.models import JoinRequest
from django.utils import timezone
from users.models import User


@pytest.mark.django_db
class TestJoinRequestConflicts:
    def test_submit_existing_member_returns_409(self, api_client, why_join_id):
        User.objects.create_user(phone_number="+12025551299", password="pass", is_member=True)
        response = api_client.post(
            "/api/community/join-request/",
            {
                "first_name": "Already",
                "last_name": "Here",
                "phone_number": "+12025551299",
                "email": "alreadyhere@example.com",
                "answers": {why_join_id: "Liberation."},
                "sms_consent": True,
                "guidelines_consent": True,
            },
            content_type="application/json",
        )
        assert response.status_code == 409
        assert response.json()["detail"][0]["code"] == "join_request.already_member"

    def test_submit_existing_member_creates_no_join_request(self, api_client, why_join_id):
        User.objects.create_user(phone_number="+12025551298", password="pass", is_member=True)
        api_client.post(
            "/api/community/join-request/",
            {
                "first_name": "Already",
                "last_name": "Here",
                "phone_number": "+12025551298",
                "email": "alreadyhere@example.com",
                "answers": {why_join_id: "Liberation."},
                "sms_consent": True,
                "guidelines_consent": True,
            },
            content_type="application/json",
        )
        assert not JoinRequest.objects.filter(phone_number="+12025551298").exists()

    def test_submit_existing_member_email_returns_409(self, api_client, why_join_id):
        User.objects.create_user(
            phone_number="+12025551300",
            password="pass",
            email="taken@example.com",
            is_member=True,
        )
        response = api_client.post(
            "/api/community/join-request/",
            {
                "first_name": "Different",
                "last_name": "Person",
                "phone_number": "+12025551301",
                "email": "TAKEN@example.com",
                "answers": {why_join_id: "Liberation."},
                "sms_consent": True,
                "guidelines_consent": True,
            },
            content_type="application/json",
        )
        assert response.status_code == 409
        assert response.json()["detail"][0]["code"] == "join_request.already_member"

    def test_submit_existing_member_email_creates_no_join_request(self, api_client, why_join_id):
        User.objects.create_user(
            phone_number="+12025551302",
            password="pass",
            email="dupe@example.com",
            is_member=True,
        )
        api_client.post(
            "/api/community/join-request/",
            {
                "first_name": "Different",
                "last_name": "Person",
                "phone_number": "+12025551303",
                "email": "dupe@example.com",
                "answers": {why_join_id: "Liberation."},
                "sms_consent": True,
                "guidelines_consent": True,
            },
            content_type="application/json",
        )
        assert not JoinRequest.objects.filter(phone_number="+12025551303").exists()

    def test_archived_user_email_can_be_reused(self, api_client, why_join_id):
        archived = User.objects.create_user(
            phone_number="+12025551304", password="pass", email="returning@example.com"
        )
        archived.archived_at = timezone.now()
        archived.save(update_fields=["archived_at"])

        response = api_client.post(
            "/api/community/join-request/",
            {
                "first_name": "Coming",
                "last_name": "Back",
                "phone_number": "+12025551305",
                "email": "returning@example.com",
                "answers": {why_join_id: "i want to return"},
                "sms_consent": True,
                "guidelines_consent": True,
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        assert JoinRequest.objects.filter(phone_number="+12025551305").exists()

    def test_archived_user_can_resubmit_join_request(self, api_client, why_join_id):
        archived = User.objects.create_user(phone_number="+12025551297", password="pass")
        archived.archived_at = timezone.now()
        archived.save(update_fields=["archived_at"])

        response = api_client.post(
            "/api/community/join-request/",
            {
                "first_name": "Coming",
                "last_name": "Back",
                "phone_number": "+12025551297",
                "email": "comingback@example.com",
                "answers": {why_join_id: "i want to return"},
                "sms_consent": True,
                "guidelines_consent": True,
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["previously_archived"] is True
        assert JoinRequest.objects.filter(phone_number="+12025551297").exists()
