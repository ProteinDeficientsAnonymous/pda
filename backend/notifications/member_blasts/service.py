import html as html_lib
import logging
import re
from datetime import timedelta
from typing import NamedTuple

from community.content.html_sanitize import sanitize_content_html
from community.validation import Code, raise_validation
from django.conf import settings
from django.db import transaction
from django.db.models import F, Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from users.models import User

from notifications.email_sender import EmailStream, get_email_sender
from notifications.email_types import BatchSendResult, validate_recipient
from notifications.models import MemberEmailBlast, MemberEmailBlastStatus

logger = logging.getLogger("pda.notifications.member_blasts")

DUPLICATE_WINDOW = timedelta(minutes=15)

_RELATIVE_URL_ATTR = re.compile(r'\b(href|src)="/(?!/)')
_LINK = re.compile(r'<a\b[^>]*?href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL)


class RenderedBlast(NamedTuple):
    html: str
    text: str


def collect_recipients() -> tuple[list[str], int]:
    emails: list[str] = []
    skipped = 0
    for email in User.objects.members().order_by("created_at").values_list("email", flat=True):
        if not email:
            skipped += 1
            continue
        try:
            validate_recipient(email)
        except ValueError:
            skipped += 1
            continue
        emails.append(email)
    return emails, skipped


def clean_body(body_html: str) -> str:
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    return _RELATIVE_URL_ATTR.sub(rf'\1="{base}/', sanitize_content_html(body_html))


def render_blast(subject: str, body_html: str) -> RenderedBlast:
    body_html = clean_body(body_html)
    with_urls = _LINK.sub(lambda m: f"{m.group(2)} ({m.group(1)})", body_html)
    body_text = html_lib.unescape(strip_tags(with_urls)).strip()
    context = {"subject": subject, "body_html": body_html, "body_text": body_text}
    return RenderedBlast(
        html=render_to_string("emails/member_blast.html", context),
        text=render_to_string("emails/member_blast.txt", context),
    )


def send_member_blast(*, sender: User, subject: str, body_html: str) -> MemberEmailBlast:
    body_html = clean_body(body_html)
    rendered = render_blast(subject, body_html)
    with transaction.atomic():
        User.objects.select_for_update().get(pk=sender.pk)
        reached_someone = Q(
            status__in=[
                MemberEmailBlastStatus.SENDING,
                MemberEmailBlastStatus.SENT,
                MemberEmailBlastStatus.UNKNOWN,
            ]
        ) | Q(status=MemberEmailBlastStatus.FAILED, failed_count__lt=F("recipient_count"))
        if MemberEmailBlast.objects.filter(
            reached_someone,
            subject=subject,
            body_html=body_html,
            created_at__gte=timezone.now() - DUPLICATE_WINDOW,
        ).exists():
            raise_validation(Code.Notification.BLAST_DUPLICATE, status_code=400)
        recipients, skipped = collect_recipients()
        if not recipients:
            raise_validation(Code.Notification.BLAST_NO_RECIPIENTS, status_code=400)
        blast = MemberEmailBlast.objects.create(
            sender=sender,
            subject=subject,
            body_html=body_html,
            recipient_count=len(recipients),
            skipped_count=skipped,
        )
    try:
        result = get_email_sender(EmailStream.BULK).send_batch(
            recipients, subject, rendered.html, rendered.text
        )
    except Exception:
        logger.error("member_blast_send_exception blast_id=%s", blast.id, exc_info=True)
        result = BatchSendResult(unknown=len(recipients))
        _finalize(blast, result)
        raise
    _finalize(blast, result)
    return blast


def _finalize(blast: MemberEmailBlast, result: BatchSendResult) -> None:
    if result.failed == result.unknown == 0:
        blast.status = MemberEmailBlastStatus.SENT
    elif result.unknown:
        blast.status = MemberEmailBlastStatus.UNKNOWN
    else:
        blast.status = MemberEmailBlastStatus.FAILED
    blast.failed_count = result.failed
    blast.unknown_count = result.unknown
    blast.finished_at = timezone.now()
    blast.save(update_fields=["status", "failed_count", "unknown_count", "finished_at"])


def send_test_blast(*, user: User, subject: str, body_html: str) -> BatchSendResult:
    if not user.email:
        raise_validation(Code.Notification.BLAST_NO_OWN_EMAIL, status_code=400)
    rendered = render_blast(subject, body_html)
    return get_email_sender(EmailStream.BULK).send_batch(
        [user.email], subject, rendered.html, rendered.text
    )
