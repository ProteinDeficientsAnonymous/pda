from community.join_requests.closing import close_tentative_requests
from django.db import transaction
from django.utils import timezone

from users._attendance_pause import release_held_events
from users.models import MembershipStatus, User


def archive_user(request, user: User) -> list[str]:
    """Archive user and release what they hold on upcoming events, as a guidelines pause does.

    param(request): the triggering request, for promoted-member email logging
    param(user): the member to archive
    return(list[str]): ids of the elevated roles that were stripped
    """
    with transaction.atomic():
        close_tentative_requests(request, user)
        # Runs before archived_at is set: release_held_events skips archived users.
        released = release_held_events(request, user, MembershipStatus.ARCHIVED)[1]
        user.archived_at = timezone.now()
        user.status_before_archive = user.membership_status
        user.calendar_token = ""
        user.save(
            update_fields=[
                "archived_at",
                "status_before_archive",
                "calendar_token",
                *user.set_membership_status(
                    MembershipStatus.ARCHIVED, by=getattr(request, "auth", None)
                ),
            ]
        )
    return released["removed_role_ids"]
