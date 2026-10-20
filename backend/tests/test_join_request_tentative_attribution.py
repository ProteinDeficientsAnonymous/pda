import importlib

import pytest
from audit.models import AuditLogEntry, AuditTargetType
from community.models import JoinRequestStatus
from django.apps import apps

pytestmark = pytest.mark.django_db

backfill = importlib.import_module("community.migrations.0100_backfill_joinrequest_tentative")


def _decide(api_client, headers, join_request, status):
    return api_client.patch(
        f"/api/community/join-requests/{join_request.id}/",
        {"status": status},
        content_type="application/json",
        **headers,
    )


def test_tentative_stamps_who_and_when(
    api_client, vettor_headers, vettor_user, sample_join_request
):
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    sample_join_request.refresh_from_db()
    assert sample_join_request.tentative_by == vettor_user
    assert sample_join_request.tentative_at is not None


def test_tentative_stamp_survives_final_approval(
    api_client, vettor_headers, vettor_user, sample_join_request
):
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)
    sample_join_request.refresh_from_db()
    assert sample_join_request.tentative_by == vettor_user
    assert sample_join_request.approved_by == vettor_user


def test_list_exposes_tentative_attribution(api_client, vettor_headers, sample_join_request):
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    response = api_client.get("/api/community/join-requests/", **vettor_headers)
    row = next(r for r in response.json() if r["id"] == str(sample_join_request.id))
    assert row["tentative_by_name"] == "Vettor"
    assert row["tentative_at"] is not None


def test_backfill_uses_latest_audit_entry(vettor_user, test_user, sample_join_request):
    sample_join_request.status = JoinRequestStatus.TENTATIVE
    sample_join_request.save()
    for actor in (test_user, vettor_user):
        AuditLogEntry.objects.create(
            action="join_request_tentative",
            actor=actor,
            actor_label=actor.full_name,
            target_type=AuditTargetType.JOIN_REQUEST,
            target_id=str(sample_join_request.id),
            level=20,
        )
    latest = AuditLogEntry.objects.order_by("-created_at").first()

    backfill.backfill_tentative(apps, None)

    sample_join_request.refresh_from_db()
    assert sample_join_request.tentative_by == latest.actor
    assert sample_join_request.tentative_at == latest.created_at
