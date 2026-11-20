from community.join_requests.closing import close_tentative_requests
from django.db import transaction

from users._attendance_pause import release_held_events
from users.models import MembershipStatus, User


def archive_user(request, user: User) -> dict:
    """Archive user and release what they hold on upcoming events, as a guidelines pause does.

    param(request): the triggering request, for promoted-member email logging
    param(user): the member to archive
    return(dict): audit details of the stripped roles and released RSVPs, host spots and drafts
    """
    with transaction.atomic():
        # Locks and re-reads the row so status_before_archive can't be stale or ARCHIVED.
        if not User.objects.select_for_update().filter(pk=user.pk, archived_at=None).exists():
            return {}
        user.refresh_from_db()
        close_tentative_requests(request, user)
        # Runs before archived_at is set: release_held_events skips archived users.
        _, released = release_held_events(request, user, MembershipStatus.ARCHIVED)
        user.save(update_fields=user.archive(by=getattr(request, "auth", None)))
    return released
