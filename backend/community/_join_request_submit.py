"""Public join-request submission and phone-check endpoints (unauthenticated)."""

import logging
from enum import StrEnum

from config.audit import audit_log
from config.ratelimit import client_ip, rate_limit
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from notifications.service import create_join_request_notifications
from pydantic import BaseModel, EmailStr, Field, field_validator
from users._name_parsing import parse_display_name
from users.models import User

from community._field_limits import FieldLimit
from community._join_requests import JoinRequestOut, _join_request_out
from community._shared import (
    ErrorOut,
    _validate_phone,
    flatten_to_single_line,
    logger,
    validate_display_name,
)
from community._validation import Code, ValidationException, raise_validation
from community.models import (
    JoinFormQuestion,
    JoinFormQuestionType,
    JoinRequest,
    JoinRequestStatus,
)

router = Router()


class JoinRequestIn(BaseModel):
    display_name: str = Field(default="", max_length=FieldLimit.DISPLAY_NAME)
    first_name: str = Field(default="", max_length=FieldLimit.FIRST_NAME)
    last_name: str = Field(default="", max_length=FieldLimit.LAST_NAME)
    phone_number: str = Field(max_length=FieldLimit.PHONE)
    email: EmailStr
    answers: dict[str, str] = {}
    # Consent timestamps are recorded on the join request for TCPA/Twilio proof (see #501).
    sms_consent: bool = False
    guidelines_consent: bool = False
    # Honeypot: a non-empty value (bots auto-fill it) flags spam.
    website: str = Field(default="", max_length=FieldLimit.DISPLAY_NAME)

    @field_validator("answers")
    @classmethod
    def validate_answer_lengths(cls, v: dict[str, str]) -> dict[str, str]:
        for key, answer in v.items():
            if len(answer) > FieldLimit.DESCRIPTION:
                raise_validation(
                    Code.JoinRequest.ANSWER_TOO_LONG,
                    field=f"answers.{key}",
                    label=key,
                    max=FieldLimit.DESCRIPTION,
                )
        return v


class CheckPhoneStatus(StrEnum):
    MEMBER = "member"
    PENDING = "pending"
    UNKNOWN = "unknown"


class CheckPhoneOut(BaseModel):
    status: CheckPhoneStatus


class CheckPhoneIn(BaseModel):
    phone_number: str = Field(max_length=FieldLimit.PHONE)


def _validate_answers(
    answers: dict[str, str],
    questions: dict[str, JoinFormQuestion],
) -> None:
    """Validate answers against questions. Raises ValidationException on failure."""
    for q_id, q in questions.items():
        answer = answers.get(q_id, "").strip()
        if q.required and not answer:
            raise_validation(
                Code.JoinRequest.ANSWER_REQUIRED,
                field=f"answers.{q_id}",
                label=q.label,
            )
        if (
            q.field_type == JoinFormQuestionType.SELECT
            and answer
            and answer not in (q.options or [])
        ):
            raise_validation(
                Code.JoinRequest.ANSWER_INVALID_OPTION,
                field=f"answers.{q_id}",
                label=q.label,
            )


def _build_custom_answers(
    answers: dict[str, str],
    questions: dict[str, JoinFormQuestion],
) -> dict:
    """Snapshot answers with their labels."""
    result = {}
    for q_id, q in questions.items():
        answer = answers.get(q_id, "").strip()
        if answer:
            result[q_id] = {"label": q.label, "answer": answer}
    return result


def _send_join_request_email(display_name: str, phone: str, custom_answers: dict) -> None:
    """Send vetting email for a new join request."""
    if not settings.VETTING_EMAIL:
        return
    try:
        # Flatten to single-line so a newline in display_name can't forge email headers.
        safe_subject = flatten_to_single_line(f"New PDA Join Request: {display_name}")
        answer_lines = "\n".join(
            f"{data['label']}: {data['answer']}" for data in custom_answers.values()
        )
        send_mail(
            subject=safe_subject,
            message=f"Display Name: {display_name}\nPhone: {phone}\n\n{answer_lines}",
            from_email=settings.DEFAULT_FROM_EMAIL or "noreply@pda.org",
            recipient_list=[settings.VETTING_EMAIL],
        )
    except Exception:
        logger.exception("Failed to send vetting email for join request")


def _honeypot_decoy_response(display_name: str, phone_number: str) -> JoinRequestOut:
    """Mimic a real submission's shape so bots register success and stop retrying."""
    return JoinRequestOut(
        id="",
        display_name=display_name,
        phone_number=phone_number,
        submitted_at=timezone.now(),
        status=JoinRequestStatus.PENDING,
    )


def _resolve_submission_user(validated_phone: str, normalized_email: str):
    """Resolve an applicant to an existing User, or None for a brand-new one.

    Archived accounts are ignored so a former member can re-join with the same
    phone/email. Phone takes precedence over email when the two point at
    different rows (spec: phone wins, log a warning).

    Raises:
      - ALREADY_MEMBER (409) when the match is an active member — they should
        sign in, not re-apply.
      - PHONE_ALREADY_PENDING (400) when a pending request already exists.

    Returns ``(matched_user, email_claimed)``: the non-member User to attach
    (or None), and whether the submitted email is already held by a *different*
    row under the unique-email constraint. The caller uses ``email_claimed`` to
    avoid backfilling an email that would violate it.
    """
    phone_user = User.objects.filter(phone_number=validated_phone, archived_at__isnull=True).first()
    email_user = (
        User.objects.filter(email=normalized_email, archived_at__isnull=True).first()
        if normalized_email
        else None
    )
    if phone_user and email_user and phone_user.pk != email_user.pk:
        logger.warning(
            "join request phone/email point at different users; phone wins (phone=%s)",
            validated_phone,
        )
    matched = phone_user or email_user

    if matched and matched.is_member:
        raise_validation(Code.JoinRequest.ALREADY_MEMBER, status_code=409)
    if JoinRequest.objects.filter(
        phone_number=validated_phone, status=JoinRequestStatus.PENDING
    ).exists():
        raise_validation(Code.JoinRequest.PHONE_ALREADY_PENDING, status_code=400)

    # The unique-email constraint ignores archived_at, so check across ALL rows
    # (archived included) — an archived account keeps its email and would still
    # collide on backfill.
    email_claimed = bool(normalized_email) and (
        User.objects.filter(email=normalized_email)
        .exclude(pk=matched.pk if matched else None)
        .exists()
    )
    return matched, email_claimed


@router.post(
    "/join-request/",
    response={201: JoinRequestOut, 400: ErrorOut, 409: ErrorOut, 422: ErrorOut, 429: ErrorOut},
    auth=None,
    operation_id="submit_join_request",
)
@rate_limit(key_func=client_ip, rate="3/h")
def submit_join_request(request, payload: JoinRequestIn):
    first_name = payload.first_name.strip()
    last_name = payload.last_name.strip()
    if not first_name and payload.display_name:
        first_name, last_name = parse_display_name(payload.display_name.strip())
    display_name = f"{first_name} {last_name}".strip() or payload.display_name.strip()

    # Honeypot trip — silently 201 without persisting so bots don't retry.
    if payload.website.strip():
        audit_log(
            logging.WARNING,
            "join_request_honeypot_tripped",
            request,
            details={"display_name": display_name},
        )
        return Status(201, _honeypot_decoy_response(display_name, payload.phone_number))

    if not payload.sms_consent:
        raise_validation(Code.JoinRequest.SMS_CONSENT_REQUIRED, field="sms_consent")

    if not payload.guidelines_consent:
        raise_validation(Code.JoinRequest.GUIDELINES_CONSENT_REQUIRED, field="guidelines_consent")

    validate_display_name(first_name, field="first_name")
    if last_name:
        validate_display_name(last_name, field="last_name")
    validated_phone = _validate_phone(payload.phone_number)
    normalized_email = payload.email.strip().lower()
    matched_user, email_claimed = _resolve_submission_user(validated_phone, normalized_email)

    questions = {str(q.id): q for q in JoinFormQuestion.objects.all()}
    _validate_answers(payload.answers, questions)

    custom_answers = _build_custom_answers(payload.answers, questions)

    with transaction.atomic():
        # Backfill the non-member's missing email so the now-known contact
        # carries onto the account when it's promoted. Skip when the email is
        # already claimed by a different user (the ambiguity was logged in
        # _resolve_submission_user) — writing it would break the unique-email
        # constraint.
        if matched_user and normalized_email and not matched_user.email and not email_claimed:
            matched_user.email = normalized_email
            matched_user.save(update_fields=["email"])

        join_request = JoinRequest.objects.create(
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            phone_number=validated_phone,
            email=normalized_email,
            user=matched_user,
            custom_answers=custom_answers,
            sms_consent_at=timezone.now(),
            guidelines_consent_at=timezone.now(),
        )

    logger.info("Join request submitted by %s", display_name)
    audit_log(
        logging.INFO,
        "join_request_submitted",
        request,
        target_type="join_request",
        target_id=str(join_request.id),
        details={"display_name": display_name},
    )
    _send_join_request_email(display_name, validated_phone, custom_answers)
    try:
        create_join_request_notifications(display_name)
    except Exception:
        logger.exception("Failed to create join request notifications")

    return Status(201, _join_request_out(join_request))


@router.post("/check-phone/", response={200: CheckPhoneOut, 429: ErrorOut}, auth=None)
@rate_limit(key_func=client_ip, rate="20/h")
def check_phone(request, payload: CheckPhoneIn):
    try:
        normalized = _validate_phone(payload.phone_number)
    except ValidationException:
        return Status(200, CheckPhoneOut(status=CheckPhoneStatus.UNKNOWN))
    if User.objects.filter(
        phone_number=normalized, is_member=True, archived_at__isnull=True
    ).exists():
        return Status(200, CheckPhoneOut(status=CheckPhoneStatus.MEMBER))
    if JoinRequest.objects.filter(
        phone_number=normalized, status=JoinRequestStatus.PENDING
    ).exists():
        return Status(200, CheckPhoneOut(status=CheckPhoneStatus.PENDING))
    return Status(200, CheckPhoneOut(status=CheckPhoneStatus.UNKNOWN))
