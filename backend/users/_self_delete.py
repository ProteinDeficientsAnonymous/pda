import logging

from community._validation import Code, raise_validation
from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.db import transaction
from django.http import HttpResponse
from ninja import Router
from ninja.responses import Status
from notifications.service import create_account_deleted_notifications

from users._archive import archive_user
from users._helpers import _is_last_admin
from users._refresh_cookie import clear_refresh_cookie
from users.schemas import DeleteAccountIn, ErrorOut

router = Router()


@router.post("/me/delete/", response={204: None, 400: ErrorOut, 429: ErrorOut}, auth=gated_jwt)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="5/m")
def delete_me(request, payload: DeleteAccountIn, response: HttpResponse):
    user = request.auth
    if not user.check_password(payload.password):
        raise_validation(Code.Auth.CURRENT_PASSWORD_INCORRECT, field="password", status_code=400)
    if _is_last_admin(user):
        raise_validation(Code.User.CANNOT_DELETE_LAST_ADMIN, status_code=400)
    with transaction.atomic():
        removed_role_ids = archive_user(request, user)
        create_account_deleted_notifications(user)
    audit_log(
        logging.WARNING,
        "user_self_deleted",
        request,
        target=AuditTarget(
            type=AuditTargetType.USER,
            id=str(user.pk),
            details={"full_name": user.full_name, "removed_role_ids": removed_role_ids},
        ),
    )
    clear_refresh_cookie(response)
    return Status(204, None)
