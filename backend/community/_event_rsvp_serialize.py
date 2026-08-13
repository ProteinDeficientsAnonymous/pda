from config.media_proxy import media_path

from community._event_schemas import EventRsvpQuestionOut
from community.models import EventRsvpQuestion, RSVPStatus


def event_rsvp_question_out(question: EventRsvpQuestion) -> EventRsvpQuestionOut:
    return EventRsvpQuestionOut(
        id=str(question.id),
        label=question.label,
        field_type=question.field_type,
        options=list(question.options or []),
        required=question.required,
        display_order=question.display_order,
    )


def preview_photo_user_ids(rsvps, limit: int = 5) -> set[str]:
    ordered = sorted(
        rsvps,
        key=lambda r: {RSVPStatus.ATTENDING: 0, RSVPStatus.MAYBE: 1}.get(r.status, 99),
    )
    ids = [
        str(r.user_id)
        for s, m in (
            (RSVPStatus.ATTENDING, True),
            (RSVPStatus.MAYBE, True),
            (RSVPStatus.ATTENDING, False),
            (RSVPStatus.MAYBE, False),
        )
        for r in ordered
        if r.status == s and r.user.is_member is m
    ]
    return set(ids[:limit])


def with_guest_photos(guests, rsvps, *, all_photos: bool):
    photo_user_ids = None if all_photos else preview_photo_user_ids(rsvps)
    users = {str(r.user_id): r.user for r in rsvps}
    for guest in guests:
        if photo_user_ids is None or guest.user_id in photo_user_ids:
            guest.photo_url = media_path(users[guest.user_id].profile_photo)
    return guests
