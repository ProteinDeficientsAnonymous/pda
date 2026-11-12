from django.db.models import Exists, OuterRef, Q

from community.models import Event


def _viewer_is_cohost(user) -> Exists:
    return Exists(Event.co_hosts.through.objects.filter(event_id=OuterRef("pk"), user_id=user.pk))


def hosted_by_q(user):
    """Rows the user created or co-hosts. A pause drops the host spot but keeps the creator."""
    return Q(created_by=user) | _viewer_is_cohost(user)


def is_hosted_by(event: Event, user) -> bool:
    """`hosted_by_q` for one loaded event; reads prefetched co_hosts when present."""
    return event.created_by_id == user.pk or any(c.pk == user.pk for c in event.co_hosts.all())
