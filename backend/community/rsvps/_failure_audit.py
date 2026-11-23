import logging
from functools import wraps

from config.audit import AuditTarget, AuditTargetType, audit_log_before_raise

from community.validation import ValidationException


def audit_rsvp_failure(view_func):
    """Audit an rsvp the member couldn't save (full, closed, bad answers, …) as rsvp_failed."""

    @wraps(view_func)
    def wrapper(request, event_id, *args, **kwargs):
        try:
            return view_func(request, event_id, *args, **kwargs)
        except ValidationException as exc:
            user = getattr(request, "auth", None)
            details = {"code": exc.code}
            if getattr(user, "pk", None):
                details["user_id"] = str(user.pk)
            audit_log_before_raise(
                logging.WARNING,
                "rsvp_failed",
                request,
                target=AuditTarget(type=AuditTargetType.EVENT, id=str(event_id), details=details),
            )
            raise

    return wrapper
