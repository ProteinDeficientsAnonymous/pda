from django.db.models import Exists, OuterRef, Q

from community.models import Event


def _cohost_rows(**filters) -> Exists:
    return Exists(Event.co_hosts.through.objects.filter(event_id=OuterRef("pk"), **filters))


def hosted_by_q(user):
    """Rows the user created or co-hosts."""
    return Q(created_by=user) | _cohost_rows(user_id=user.pk)


def draft_host_q(user):
    """Drafts the user co-hosts, or created and a pause left hostless (removals keep one host)."""
    return (Q(created_by=user) & ~_cohost_rows()) | _cohost_rows(user_id=user.pk)


def is_draft_host(event: Event, user) -> bool:
    """`draft_host_q` for one loaded event; reads prefetched co_hosts when present."""
    co_host_ids = {c.pk for c in event.co_hosts.all()}
    return user.pk in co_host_ids or (event.created_by_id == user.pk and not co_host_ids)
