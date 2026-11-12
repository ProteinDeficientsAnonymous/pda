import logging

from community.validation import Code, raise_validation
from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import HARD_ACCOUNT_BLOCKS, account_block_code

from users.models import User

_AUDIT_SUFFIX = {
    Code.Auth.ACCOUNT_ARCHIVED: "archived",
    Code.Auth.ACCOUNT_GUIDELINES_PAUSED: "paused",
    Code.Auth.NOT_A_MEMBER: "not_a_member",
}


def reject_blocked_login(request, user: User, audit_prefix: str) -> None:
    """Audit and raise 403 when the account may not sign in at all.

    param(audit_prefix): "login" or "magic_login"; the action becomes e.g. login_archived
    """
    code = account_block_code(user)
    if code not in HARD_ACCOUNT_BLOCKS:
        return
    audit_log(
        logging.WARNING,
        f"{audit_prefix}_{_AUDIT_SUFFIX[code]}",
        request,
        target=AuditTarget(type=AuditTargetType.USER, id=str(user.pk)),
    )
    raise_validation(code, status_code=403)
