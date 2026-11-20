import uuid

import pytest
from community.validation import InvalidStateTransition
from django.utils import timezone
from hypothesis import given, settings
from hypothesis import strategies as st
from users._transitions import transition_membership
from users.models import PAUSED_STATUSES, MembershipEvent, MembershipStatus, User

_LIVE_STATUSES = [s for s in MembershipStatus if s != MembershipStatus.ARCHIVED]
_FIELDS = [f for f in User._meta.concrete_fields if not f.primary_key]


def _user(status: MembershipStatus, before_archive: MembershipStatus | None) -> User:
    archived = before_archive is not None
    paused = MembershipStatus.ATTENDANCE_PAUSED in (status, before_archive)
    return User(
        id=uuid.uuid4(),
        phone_number="+13125559998",
        membership_status=MembershipStatus.ARCHIVED if archived else status,
        archived_at=timezone.now() if archived else None,
        status_before_archive=before_archive,
        attendance_paused_at=timezone.now() if paused else None,
        has_joined_whatsapp=True,
        calendar_token="cal-tok",
    )


def _values(user: User) -> dict[str, object]:
    return {f.name: getattr(user, f.attname) for f in _FIELDS}


@pytest.mark.unit
@settings(max_examples=200, deadline=None)
@given(
    status=st.sampled_from(_LIVE_STATUSES),
    before_archive=st.none() | st.sampled_from([MembershipStatus.ACTIVE_MEMBER, *PAUSED_STATUSES]),
    events=st.lists(st.sampled_from(list(MembershipEvent)), min_size=1, max_size=12),
)
def test_every_changed_field_is_in_update_fields(status, before_archive, events):
    # a field changed in memory but missing from update_fields is silently never saved
    user = _user(status, before_archive)
    actor = _user(MembershipStatus.ACTIVE_MEMBER, None)
    for event in events:
        before = _values(user)
        try:
            update_fields = transition_membership(user, event, by=actor)
        except InvalidStateTransition:
            assert _values(user) == before
            continue
        after = _values(user)
        changed = {name for name in after if after[name] != before[name]}
        assert changed <= set(update_fields), (
            f"{event}: {changed - set(update_fields)} not in update_fields"
        )
