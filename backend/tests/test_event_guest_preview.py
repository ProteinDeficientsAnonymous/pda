from types import SimpleNamespace

import pytest
from community._event_rsvp_serialize import GUEST_PREVIEW_LIMIT, preview_photo_user_ids
from community.models import RSVPStatus


def _rsvp(user_id: str, status: str, is_member: bool) -> SimpleNamespace:
    return SimpleNamespace(
        user_id=user_id,
        status=status,
        user=SimpleNamespace(is_member=is_member),
    )


@pytest.mark.unit
def test_preview_photo_user_ids_prefers_attending_members_then_maybe():
    rsvps = [
        _rsvp("wait", RSVPStatus.WAITLISTED, True),
        _rsvp("n1", RSVPStatus.ATTENDING, False),
        _rsvp("m1", RSVPStatus.ATTENDING, True),
        _rsvp("mm", RSVPStatus.MAYBE, True),
        _rsvp("n2", RSVPStatus.ATTENDING, False),
        _rsvp("nm", RSVPStatus.MAYBE, False),
        _rsvp("m2", RSVPStatus.ATTENDING, True),
        _rsvp("n3", RSVPStatus.ATTENDING, False),
    ]
    assert preview_photo_user_ids(rsvps) == {"m1", "m2", "mm", "n1", "n2"}
    assert GUEST_PREVIEW_LIMIT == 5
