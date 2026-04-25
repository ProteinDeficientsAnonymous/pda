"""Welcome message template endpoints.

Plain-text template stored as a singleton (pk=1). Read by any authed user
(vetters need it to render the message); edited by users with
EDIT_WELCOME_MESSAGE.
"""

import logging
from datetime import datetime

from config.audit import audit_log
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from community._field_limits import FieldLimit
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import WelcomeMessageTemplate

router = Router()


class WelcomeTemplateOut(BaseModel):
    body: str
    updated_at: datetime


class WelcomeTemplatePatchIn(BaseModel):
    # Length validated explicitly in the handler so we can raise with our
    # structured WelcomeTemplate.BODY_TOO_LONG code (Pydantic's max_length
    # would emit a generic shape and skip our copy).
    body: str | None = Field(default=None)


def _out(obj: WelcomeMessageTemplate) -> WelcomeTemplateOut:
    return WelcomeTemplateOut(body=obj.body, updated_at=obj.updated_at)


@router.get("/welcome-template/", response={200: WelcomeTemplateOut}, auth=JWTAuth())
def get_welcome_template(request):
    return Status(200, _out(WelcomeMessageTemplate.get()))


@router.patch(
    "/welcome-template/",
    response={200: WelcomeTemplateOut, 403: ErrorOut, 422: ErrorOut},
    auth=JWTAuth(),
)
def update_welcome_template(request, payload: WelcomeTemplatePatchIn):
    if not request.auth.has_permission(PermissionKey.EDIT_WELCOME_MESSAGE):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "update_welcome_template",
                "required_permission": PermissionKey.EDIT_WELCOME_MESSAGE,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="edit_welcome_message")

    if payload.body is None or not payload.body.strip():
        raise_validation(Code.WelcomeTemplate.BODY_REQUIRED, field="body")

    if len(payload.body) > FieldLimit.WELCOME_TEMPLATE:
        raise_validation(
            Code.WelcomeTemplate.BODY_TOO_LONG,
            field="body",
            max_length=FieldLimit.WELCOME_TEMPLATE,
        )

    template = WelcomeMessageTemplate.get()
    template.body = payload.body
    template.save()
    audit_log(
        logging.INFO,
        "welcome_template_updated",
        request,
        target_type="welcome_template",
    )
    return Status(200, _out(template))
