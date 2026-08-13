from collections.abc import Iterable

from config.media_proxy import media_path

from community._event_schemas import EventRsvpQuestionOut, RSVPGuestOut
from community.models import EventRsvpQuestion, RSVPStatus

# Keep in sync with frontend PREVIEW_LIMIT in guestSort.ts (members-first going/maybe chips).
GUEST_PREVIEW_LIMIT = 5

_PREVIEW_TIERS = (
    (RSVPStatus.ATTENDING, True),
    (RSVPStatus.MAYBE, True),
    (RSVPStatus.ATTENDING, False),
    (RSVPStatus.MAYBE, False),
)


def event_rsvp_question_out(question: EventRsvpQuestion) -> EventRsvpQuestionOut:
    return EventRsvpQuestionOut(
        id=str(question.id),
        label=question.label,
        field_type=question.field_type,
        options=list(question.options or []),
        required=question.required,
        display_order=question.display_order,
    )


def preview_photo_user_ids(rsvps: Iterable, limit: int = GUEST_PREVIEW_LIMIT) -> set[str]:
    ordered = sorted(
        rsvps,
        key=lambda r: {RSVPStatus.ATTENDING: 0, RSVPStatus.MAYBE: 1}.get(r.status, 99),
    )
    ids: list[str] = []
    for status, is_member in _PREVIEW_TIERS:
        ids.extend(
            str(r.user_id) for r in ordered if r.status == status and r.user.is_member is is_member
        )
    return set(ids[:limit])


def with_guest_photos(
    guests: list[RSVPGuestOut], rsvps: Iterable, *, all_photos: bool
) -> list[RSVPGuestOut]:
    # Skip B2 signing except five preview guests — that work dominates event-detail cost.
    photo_user_ids = None if all_photos else preview_photo_user_ids(rsvps)
    users = {str(r.user_id): r.user for r in rsvps}
    for guest in guests:
        if photo_user_ids is None or guest.user_id in photo_user_ids:
            guest.photo_url = media_path(users[guest.user_id].profile_photo)
    return guests
