from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from typing import NamedTuple

from django.db.models import Prefetch
from pydantic import BaseModel
from users.models import User

from community.models import EventRSVP, JoinRequest, JoinRequestStatus


class PreviousRejectionOut(BaseModel):
    status_changed_at: datetime | None = None
    status_changed_by_name: str | None = None
    rejection_reason: str = ""
    rejection_note: str = ""


class PreviousArchiveOut(BaseModel):
    archived_at: datetime | None = None
    archived_by_name: str | None = None


class PhoneLookups(NamedTuple):
    users_by_phone: dict[str, User]
    rejections_by_phone: dict[str, list[JoinRequest]]


def phone_lookups(join_requests: Iterable[JoinRequest]) -> PhoneLookups:
    """Users (with rsvps) and rejected requests, newest first, for every phone in the batch."""
    phones = {jr.phone_number for jr in join_requests}
    users = (
        User.objects.filter(phone_number__in=phones)
        .select_related("membership_status_changed_by")
        .prefetch_related(
            Prefetch("event_rsvps", queryset=EventRSVP.objects.select_related("event"))
        )
    )
    rejected = (
        JoinRequest.objects.filter(phone_number__in=phones, status=JoinRequestStatus.REJECTED)
        .select_related("status_changed_by")
        .order_by("-submitted_at")
    )
    rejections: dict[str, list[JoinRequest]] = defaultdict(list)
    for rejection in rejected:
        rejections[rejection.phone_number].append(rejection)
    return PhoneLookups({u.phone_number: u for u in users}, rejections)


class PhoneHistory(NamedTuple):
    phone_user: User | None
    previous_archive: PreviousArchiveOut | None
    previous_rejection: JoinRequest | None


def previous_archive_out(user: User | None) -> PreviousArchiveOut | None:
    """While archived, the last status change is the archive itself."""
    if user is None or user.archived_at is None:
        return None
    by = user.membership_status_changed_by
    return PreviousArchiveOut(
        archived_at=user.archived_at, archived_by_name=by.full_name if by else None
    )


def phone_history(jr: JoinRequest, lookups: PhoneLookups) -> PhoneHistory:
    phone_user = lookups.users_by_phone.get(jr.phone_number)
    rejections = lookups.rejections_by_phone.get(jr.phone_number, [])
    return PhoneHistory(
        phone_user=phone_user,
        previous_archive=previous_archive_out(phone_user),
        previous_rejection=next((r for r in rejections if r.submitted_at < jr.submitted_at), None),
    )


def previous_rejection_out(rejection: JoinRequest | None) -> PreviousRejectionOut | None:
    if rejection is None:
        return None
    by = rejection.status_changed_by
    return PreviousRejectionOut(
        status_changed_at=rejection.status_changed_at,
        status_changed_by_name=by.full_name if by else None,
        rejection_reason=rejection.rejection_reason,
        rejection_note=rejection.rejection_note,
    )
