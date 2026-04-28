"""Helpers for the event text-blast flow.

Kept separate from `_event_blasts.py` so the endpoint module stays focused on
HTTP shapes and this module stays focused on the recipient resolution + send
loop. Both modules together implement the feature in #403.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from community.models import (
    EventBlastMute,
    EventRSVP,
    EventTextBlast,
    EventTextBlastDelivery,
    EventTextBlastDeliveryStatus,
    RecipientFilterSentinel,
    RSVPStatus,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from users.models import User as UserModel

    from community.models import Event

# Hard ceiling on lifetime text blasts per event. Past 5 we 400 with
# Code.TextBlast.EVENT_LIMIT_REACHED so the host can't accidentally spam an
# event's attendees beyond a reasonable burst.
MAX_BLASTS_PER_EVENT = 5

# Suffix appended to every outbound SMS body. Single source of truth so tests
# can pin behavior; the body the host typed is stored pre-suffix on the
# EventTextBlast row so we can iterate on this without rewriting history.
_MUTE_SUFFIX = "\n\n(reply M to mute messages for this event)"

# Filter values accepted in the per-blast `recipient_filters` list. RSVPStatus
# values + the INVITED_NO_RESPONSE sentinel for "invited but no RSVP yet".
_VALID_FILTERS: frozenset[str] = frozenset(
    {*RSVPStatus.values, RecipientFilterSentinel.INVITED_NO_RESPONSE}
)


def can_send_event_blast(requesting_user, creator, co_host_ids: set[str]) -> bool:
    """Creator + accepted co-hosts can send blasts. Admins are NOT included —
    text blasts are a host-only workflow, not a moderation surface.
    """
    if requesting_user is None:
        return False
    if creator is not None and requesting_user.pk == creator.pk:
        return True
    return str(requesting_user.pk) in co_host_ids


def validate_filters(filters: list[str]) -> None:
    """Raise INVALID_FILTER if any filter value is unrecognized."""
    from community._validation import Code, raise_validation

    for f in filters:
        if f not in _VALID_FILTERS:
            raise_validation(
                Code.TextBlast.INVALID_FILTER,
                field="recipient_filters",
                status_code=422,
            )


def resolve_recipients(event: Event, filters: list[str], sender: UserModel) -> list[UserModel]:
    """Return the deduped list of users to text for this blast.

    Union of:
    - Each RSVPStatus filter → users with an RSVP at that status.
    - INVITED_NO_RESPONSE → users in event.invited_users without any RSVP row.

    Then exclude:
    - The sender themselves (don't text yourself).
    - Users with a per-event mute (EventBlastMute).
    - Users with an empty phone_number (defensive — phone is required at signup).
    """
    rsvp_filters = [f for f in filters if f in RSVPStatus.values]
    include_no_response = RecipientFilterSentinel.INVITED_NO_RESPONSE in filters

    user_ids: set[str] = set()
    if rsvp_filters:
        rsvps = EventRSVP.objects.filter(event=event, status__in=rsvp_filters).values_list(
            "user_id", flat=True
        )
        user_ids.update(str(uid) for uid in rsvps)
    if include_no_response:
        rsvped_ids = set(EventRSVP.objects.filter(event=event).values_list("user_id", flat=True))
        invited = event.invited_users.exclude(pk__in=rsvped_ids).values_list("pk", flat=True)
        user_ids.update(str(uid) for uid in invited)

    user_ids.discard(str(sender.pk))
    muted_ids = set(EventBlastMute.objects.filter(event=event).values_list("user_id", flat=True))
    user_ids.difference_update(str(uid) for uid in muted_ids)

    from users.models import User

    return list(User.objects.filter(pk__in=user_ids).exclude(phone_number=""))


def compose_outbound_body(message: str, sender_name: str) -> str:
    """Wrap the host's message with a `pda · {sender}:` from-line and the
    mute-instruction suffix.

    The from-line is the v1 workaround for not having alphanumeric sender ID
    in the US — recipients see a phone number, but the body itself identifies
    the source. Tracked for later via #406 (A2P 10DLC brand registration).
    """
    return f"pda · {sender_name}: {message}{_MUTE_SUFFIX}"


def create_blast_with_deliveries(
    event: Event,
    sender: UserModel,
    message: str,
    filters: list[str],
    recipients: list[UserModel],
) -> EventTextBlast:
    """Create the EventTextBlast + per-recipient EventTextBlastDelivery rows
    in QUEUED status. Wrapped in a transaction so the audit trail is atomic
    even if the subsequent Twilio send loop fails partway."""
    with transaction.atomic():
        blast = EventTextBlast.objects.create(
            event=event,
            sender=sender,
            message=message,
            recipient_filters=list(filters),
            recipient_count=len(recipients),
        )
        EventTextBlastDelivery.objects.bulk_create(
            EventTextBlastDelivery(
                blast=blast,
                recipient=user,
                phone_number=user.phone_number,
                status=EventTextBlastDeliveryStatus.QUEUED,
            )
            for user in recipients
        )
    return blast


def send_blast_to_recipients(blast: EventTextBlast, body: str) -> int:
    """Iterate the blast's QUEUED deliveries, call Twilio, update each row.

    Returns the count of FAILED deliveries so the caller can fire a
    notification. Twilio failures don't roll back any prior deliveries —
    each row is its own success/failure record.
    """
    from community._sms import send_sms

    failure_count = 0
    deliveries = list(blast.deliveries.filter(status=EventTextBlastDeliveryStatus.QUEUED))
    for delivery in deliveries:
        if _attempt_send(delivery, body, send_sms):
            continue
        failure_count += 1
    return failure_count


def _attempt_send(
    delivery: EventTextBlastDelivery,
    body: str,
    send_sms,
) -> bool:
    """Try to send one SMS. True on success, False on failure (delivery row updated either way)."""
    try:
        sid = send_sms(delivery.phone_number, body)
    except Exception as e:  # noqa: BLE001 — record any Twilio error as a per-recipient failure
        delivery.status = EventTextBlastDeliveryStatus.FAILED
        delivery.error_message = str(e)[:500]
        delivery.save(update_fields=["status", "error_message"])
        return False
    delivery.status = EventTextBlastDeliveryStatus.SENT
    delivery.twilio_message_sid = sid
    delivery.save(update_fields=["status", "twilio_message_sid"])
    return True


def mask_phone(e164: str) -> str:
    """Return a masked phone like `•••1234` for the host's per-recipient list.

    Even hosts shouldn't see other people's full phones in this surface —
    the existing guest list already exposes phones to hosts in a different
    surface; this one defaults to least-privilege.
    """
    if len(e164) <= 4:
        return e164
    return "•••" + e164[-4:]


def event_blast_count(event: Event) -> int:
    """Lifetime blast count for an event — used to enforce MAX_BLASTS_PER_EVENT."""
    return EventTextBlast.objects.filter(event=event).count()


def find_inbound_event(
    phone_number: str,
) -> tuple[EventTextBlast | None, EventTextBlastDelivery | None]:
    """Find the most recent blast a phone received. Used by the inbound webhook
    to figure out which event a "M" reply should mute.

    Returns (blast, delivery) tuple. Both None if the phone has no delivery
    history (not in the system, or just hasn't received a blast).
    """
    delivery = (
        EventTextBlastDelivery.objects.filter(phone_number=phone_number)
        .select_related("blast__event")
        .order_by("-created_at")
        .first()
    )
    if delivery is None:
        return None, None
    return delivery.blast, delivery


def _ignored_recipient_filter_strings() -> Iterable[str]:
    """Lint-only stub — used by tests to assert constants stay aligned."""
    return _VALID_FILTERS
