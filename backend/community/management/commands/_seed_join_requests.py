"""Join form question + join request seeding for staging (and shared helpers)."""

from datetime import timedelta

from django.utils import timezone
from users.models import User

from community.models import JoinFormQuestion, JoinRequest, JoinRequestStatus

from ._seed_data import SEED_JOIN_FORM_QUESTIONS
from ._seed_staging_data import JOIN_REQUEST_SPECS, JoinRequestSpec, joinreq_email, joinreq_phone


def reset_join_requests() -> None:
    JoinRequest.objects.filter(phone_number__startswith="+170255504").delete()


def seed_join_form_questions(stdout) -> dict[str, JoinFormQuestion]:
    """Ensure default join form questions exist. Returns label→question mapping."""
    questions: dict[str, JoinFormQuestion] = {}
    for data in SEED_JOIN_FORM_QUESTIONS:
        question, created = JoinFormQuestion.objects.get_or_create(
            label=data.label,
            defaults={
                "field_type": data.field_type,
                "required": data.required,
                "options": data.options,
                "display_order": data.display_order,
            },
        )
        if not created and question.field_type != data.field_type:
            question.field_type = data.field_type
            question.save(update_fields=["field_type"])
        stdout.write(f"  {'created' if created else 'exists'} question: {question.label}")
        questions[question.label] = question
    return questions


def _custom_answers(spec: JoinRequestSpec, questions_by_label: dict[str, JoinFormQuestion]) -> dict:
    """Map each seeded answer onto the matching join-form question by label."""
    return {
        str(questions_by_label[label].id): {"label": label, "answer": answer}
        for label, answer in spec.answers.items()
    }


def _reviewer_fields(spec, reviewer: User | None, submitted_at) -> dict:
    if spec.status == JoinRequestStatus.APPROVED:
        return {"approved_at": submitted_at + timedelta(days=1), "approved_by": reviewer}
    if spec.status == JoinRequestStatus.REJECTED:
        return {"rejected_at": submitted_at + timedelta(days=1), "rejected_by": reviewer}
    return {}


def seed_join_requests(
    stdout,
    reviewer: User | None,
    questions_by_label: dict[str, JoinFormQuestion],
) -> list[JoinRequest]:
    now = timezone.now()
    requests: list[JoinRequest] = []
    for index, spec in enumerate(JOIN_REQUEST_SPECS):
        submitted_at = now - timedelta(days=spec.days_ago)
        answers = _custom_answers(spec, questions_by_label)
        join_request, created = JoinRequest.objects.get_or_create(
            phone_number=joinreq_phone(index),
            defaults={
                "first_name": spec.first_name,
                "last_name": spec.last_name,
                "email": joinreq_email(index) if spec.has_email else "",
                "custom_answers": answers,
                "status": spec.status,
                "sms_consent_at": submitted_at,
                "guidelines_consent_at": submitted_at,
                **_reviewer_fields(spec, reviewer, submitted_at),
            },
        )
        if created:
            JoinRequest.objects.filter(pk=join_request.pk).update(submitted_at=submitted_at)
        elif join_request.custom_answers != answers:
            join_request.custom_answers = answers
            join_request.save(update_fields=["custom_answers"])
        requests.append(join_request)
        stdout.write(
            f"  {'created' if created else 'exists'} join request: {join_request.full_name}"
        )
    return requests
