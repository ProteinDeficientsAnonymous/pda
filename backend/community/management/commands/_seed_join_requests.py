"""Join request seeding for the `seed_staging` command."""

from datetime import timedelta

from django.utils import timezone
from users.models import User

from community.models import JoinFormQuestion, JoinRequest, JoinRequestStatus

from ._seed_staging_data import JOIN_REQUEST_SPECS, joinreq_email, joinreq_phone


def reset_join_requests() -> None:
    JoinRequest.objects.filter(phone_number__startswith="+170255504").delete()


def _custom_answers(spec) -> dict:
    question = JoinFormQuestion.objects.filter(required=True).first()
    if question is None:
        return {}
    return {str(question.id): {"label": question.label, "answer": spec.answer}}


def _reviewer_fields(spec, reviewer: User | None, submitted_at) -> dict:
    if spec.status == JoinRequestStatus.APPROVED:
        return {"approved_at": submitted_at + timedelta(days=1), "approved_by": reviewer}
    if spec.status == JoinRequestStatus.REJECTED:
        return {"rejected_at": submitted_at + timedelta(days=1), "rejected_by": reviewer}
    return {}


def seed_join_requests(stdout, reviewer: User | None) -> list[JoinRequest]:
    now = timezone.now()
    requests: list[JoinRequest] = []
    for index, spec in enumerate(JOIN_REQUEST_SPECS):
        submitted_at = now - timedelta(days=spec.days_ago)
        join_request, created = JoinRequest.objects.get_or_create(
            phone_number=joinreq_phone(index),
            defaults={
                "first_name": spec.first_name,
                "last_name": spec.last_name,
                "email": joinreq_email(index) if spec.has_email else "",
                "custom_answers": _custom_answers(spec),
                "status": spec.status,
                "sms_consent_at": submitted_at,
                "guidelines_consent_at": submitted_at,
                **_reviewer_fields(spec, reviewer, submitted_at),
            },
        )
        if created:
            JoinRequest.objects.filter(pk=join_request.pk).update(submitted_at=submitted_at)
        requests.append(join_request)
        stdout.write(
            f"  {'created' if created else 'exists'} join request: {join_request.full_name}"
        )
    return requests
