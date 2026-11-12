"""Public join-request submission and phone-check endpoints (unauthenticated)."""

import logging
import uuid
from datetime import datetime
from enum import StrEnum

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.ratelimit import client_ip, rate_limit
from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from notifications.service import create_join_request_notifications
from pydantic import BaseModel, EmailStr, Field, field_validator
from users.models import PUBLIC_FORM_PHONE_REGION, User, can_sign_in_q, validate_phone

from community._question_answers import (
    assert_checkbox_members,
    assert_single_choice_member,
    checkbox_values,
    is_answer_empty,
)
from community.field_limits import FieldLimit
from community.models import (
    OPEN_JOIN_REQUEST_STATUSES,
    JoinFormQuestion,
    JoinFormQuestionType,
    JoinRequest,
    JoinRequestStatus,
)
from community.shared import (
    ErrorOut,
    flatten_to_single_line,
    logger,
    validate_display_name,
)
from community.validation import Code, ValidationException, raise_validation

router = Router()

JoinAnswerIn = str | list[str]


class JoinRequestIn(BaseModel):
    first_name: str = Field(default="", max_length=FieldLimit.FIRST_NAME)
    last_name: str = Field(default="", max_length=FieldLimit.LAST_NAME)
    phone_number: str = Field(max_length=FieldLimit.PHONE)
    email: EmailStr
    answers: dict[str, JoinAnswerIn] = {}
    # Consent timestamps are recorded on the join request for TCPA/Twilio proof (see #501).
    sms_consent: bool = False
    guidelines_consent: bool = False
    # Honeypot: a non-empty value (bots auto-fill it) flags spam.
    website: str = Field(default="", max_length=FieldLimit.DISPLAY_NAME)

    @field_validator("answers")
    @classmethod
    def validate_answer_lengths(cls, v: dict[str, JoinAnswerIn]) -> dict[str, JoinAnswerIn]:
        for key, answer in v.items():
            if len("".join(answer)) > FieldLimit.DESCRIPTION:
                raise_validation(
                    Code.JoinRequest.ANSWER_TOO_LONG,
                    field=f"answers.{key}",
                    label=key,
                    max=FieldLimit.DESCRIPTION,
                )
        return v


class JoinRequestSubmittedOut(BaseModel):
    id: str
    first_name: str
    full_name: str
    status: str
    submitted_at: datetime


def submitted_join_request_out(jr: JoinRequest) -> JoinRequestSubmittedOut:
    """Public echo of a submission — never the admin JoinRequestOut, which leaks matched-user history."""
    return JoinRequestSubmittedOut(
        id=str(jr.id),
        first_name=jr.first_name,
        full_name=jr.full_name,
        status=jr.status,
        submitted_at=jr.submitted_at,
    )


class CheckPhoneStatus(StrEnum):
    # "member" means "this number can sign in" — full members and tentatively
    # approved applicants both have an account, so both get the password step.
    MEMBER = "member"
    PENDING = "pending"
    UNKNOWN = "unknown"


class CheckPhoneOut(BaseModel):
    status: CheckPhoneStatus


class CheckPhoneIn(BaseModel):
    phone_number: str = Field(max_length=FieldLimit.PHONE)


def _normalize_answer(q: JoinFormQuestion, answer: JoinAnswerIn, field: str) -> JoinAnswerIn:
    if q.field_type == JoinFormQuestionType.CHECKBOX:
        code = Code.JoinRequest.ANSWER_INVALID_OPTION
        assert_checkbox_members(answer, q.options, code=code, field=field, label=q.label)
        return list(dict.fromkeys(checkbox_values(answer)))
    if isinstance(answer, list):
        raise_validation(Code.JoinRequest.ANSWER_INVALID_FORMAT, field=field, label=q.label)
    text = answer.strip()
    if q.field_type == JoinFormQuestionType.SELECT and text:
        code = Code.JoinRequest.ANSWER_INVALID_OPTION
        assert_single_choice_member(text, q.options, code=code, field=field, label=q.label)
    return text


def _build_custom_answers(
    answers: dict[str, JoinAnswerIn],
    questions: dict[str, JoinFormQuestion],
) -> dict:
    """Validate answers and snapshot them with their labels. Raises ValidationException."""
    result = {}
    for q_id, q in questions.items():
        field = f"answers.{q_id}"
        answer = _normalize_answer(q, answers.get(q_id, ""), field)
        if is_answer_empty(answer):
            if q.required:
                raise_validation(Code.JoinRequest.ANSWER_REQUIRED, field=field, label=q.label)
            continue
        result[q_id] = {"label": q.label, "answer": answer}
    return result


def _format_answer(answer: JoinAnswerIn) -> str:
    return ", ".join(answer) if isinstance(answer, list) else answer


def send_join_request_email(full_name: str, phone: str, custom_answers: dict) -> None:
    """Send vetting email for a new join request."""
    if not settings.VETTING_EMAIL:
        return
    try:
        # Flatten to single-line so a newline in the name can't forge email headers.
        safe_subject = flatten_to_single_line(f"New PDA Join Request: {full_name}")
        answer_lines = "\n".join(
            f"{data['label']}: {_format_answer(data['answer'])}" for data in custom_answers.values()
        )
        send_mail(
            subject=safe_subject,
            message=f"Name: {full_name}\nPhone: {phone}\n\n{answer_lines}",
            from_email=settings.DEFAULT_FROM_EMAIL or "noreply@pda.org",
            recipient_list=[settings.VETTING_EMAIL],
        )
    except Exception:
        logger.exception("Failed to send vetting email for join request")


def _honeypot_decoy_response(first_name: str, full_name: str) -> JoinRequestSubmittedOut:
    """Mimic a real submission's shape so bots register success and stop retrying."""
    return JoinRequestSubmittedOut(
        id=str(uuid.uuid4()),
        first_name=first_name,
        full_name=full_name,
        submitted_at=timezone.now(),
        status=JoinRequestStatus.PENDING,
    )


def _raise_if_open_request(validated_phone: str) -> None:
    live_statuses = set(
        JoinRequest.objects.filter(
            phone_number=validated_phone,
            status__in=OPEN_JOIN_REQUEST_STATUSES,
        ).values_list("status", flat=True)
    )
    if JoinRequestStatus.PENDING in live_statuses:
        raise_validation(Code.JoinRequest.PHONE_ALREADY_PENDING, status_code=400)
    if JoinRequestStatus.TENTATIVE in live_statuses:
        raise_validation(Code.JoinRequest.PHONE_ALREADY_TENTATIVE, status_code=400)


def _resolve_submission_user(validated_phone: str, normalized_email: str):
    """Resolve an applicant to an existing User, or None for a brand-new one.

    Archived accounts are ignored so a former member can re-join with the same
    phone/email. Phone takes precedence over email when the two point at
    different rows (spec: phone wins, log a warning).

    Raises:
      - ALREADY_MEMBER (409) when the match is a member or paused — they should
        sign in, not re-apply; login tells a paused user they're paused.
      - PHONE_ALREADY_PENDING (400) when a pending request already exists.
      - PHONE_ALREADY_TENTATIVE (400) when a tentative request already exists —
        they have an account and should sign in. A rejected request is the only
        decided state that lets someone re-apply.

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

    if matched and (
        matched.is_member
        or matched.is_guidelines_paused
        or matched.attendance_paused_at is not None
    ):
        raise_validation(Code.JoinRequest.ALREADY_MEMBER, status_code=409)
    _raise_if_open_request(validated_phone)

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
    response={
        201: JoinRequestSubmittedOut,
        400: ErrorOut,
        409: ErrorOut,
        422: ErrorOut,
        429: ErrorOut,
    },
    auth=None,
    operation_id="submit_join_request",
)
@rate_limit(key_func=client_ip, rate="3/h")
def submit_join_request(request, payload: JoinRequestIn):
    first_name = payload.first_name.strip()
    last_name = payload.last_name.strip()
    full_name = f"{first_name} {last_name}".strip()

    # Honeypot trip — silently 201 without persisting so bots don't retry.
    if payload.website.strip():
        audit_log(
            logging.WARNING,
            "join_request_honeypot_tripped",
            request,
            persist=False,
            target=AuditTarget(details={"full_name": full_name}),
        )
        return Status(201, _honeypot_decoy_response(first_name, full_name))

    if not payload.sms_consent:
        raise_validation(Code.JoinRequest.SMS_CONSENT_REQUIRED, field="sms_consent")

    if not payload.guidelines_consent:
        raise_validation(Code.JoinRequest.GUIDELINES_CONSENT_REQUIRED, field="guidelines_consent")

    validate_display_name(first_name, field="first_name")
    if last_name:
        validate_display_name(last_name, field="last_name")
    validated_phone = validate_phone(payload.phone_number, PUBLIC_FORM_PHONE_REGION)
    normalized_email = payload.email.strip().lower()
    matched_user, email_claimed = _resolve_submission_user(validated_phone, normalized_email)

    questions = {str(q.id): q for q in JoinFormQuestion.objects.all()}
    custom_answers = _build_custom_answers(payload.answers, questions)

    now = timezone.now()
    join_request = JoinRequest(
        first_name=first_name,
        last_name=last_name,
        phone_number=validated_phone,
        email=normalized_email,
        user=matched_user,
        custom_answers=custom_answers,
        sms_consent_at=now,
        guidelines_consent_at=now,
        submitted_at=now,
    )
    try:
        with transaction.atomic():
            # Backfill the non-member's missing email so the now-known contact
            # carries onto the account when it's promoted. Skip when the email is
            # already claimed by a different user (the ambiguity was logged in
            # _resolve_submission_user) — writing it would break the unique-email
            # constraint.
            if matched_user and normalized_email and not matched_user.email and not email_claimed:
                matched_user.email = normalized_email
                matched_user.save(update_fields=["email"])
            join_request.save()
    except IntegrityError:
        # A concurrent submission won the open-request unique constraint.
        _raise_if_open_request(validated_phone)
        raise

    logger.info("Join request submitted by %s", full_name)
    audit_log(
        logging.INFO,
        "join_request_submitted",
        request,
        target=AuditTarget(
            type=AuditTargetType.JOIN_REQUEST,
            id=str(join_request.id),
            details={"full_name": full_name},
        ),
    )
    send_join_request_email(full_name, validated_phone, custom_answers)
    try:
        create_join_request_notifications(full_name)
    except Exception:
        logger.exception("Failed to create join request notifications")

    return Status(201, submitted_join_request_out(join_request))


@router.post("/check-phone/", response={200: CheckPhoneOut, 429: ErrorOut}, auth=None)
@rate_limit(key_func=client_ip, rate="20/h")
def check_phone(request, payload: CheckPhoneIn):
    try:
        normalized = validate_phone(payload.phone_number, PUBLIC_FORM_PHONE_REGION)
    except ValidationException:
        return Status(200, CheckPhoneOut(status=CheckPhoneStatus.UNKNOWN))
    if (
        User.objects.filter(phone_number=normalized, archived_at__isnull=True)
        .filter(can_sign_in_q())
        .exists()
    ):
        return Status(200, CheckPhoneOut(status=CheckPhoneStatus.MEMBER))
    if JoinRequest.objects.filter(
        phone_number=normalized, status=JoinRequestStatus.PENDING
    ).exists():
        return Status(200, CheckPhoneOut(status=CheckPhoneStatus.PENDING))
    return Status(200, CheckPhoneOut(status=CheckPhoneStatus.UNKNOWN))
