import logging
from datetime import datetime

from config.audit import audit_log
from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from community._field_limits import FieldLimit
from community._shared import ErrorOut, validate_whatsapp_url
from community._validation import Code, raise_validation
from community.models import WhatsAppLinkConfig

router = Router()


class WhatsAppLinkOut(BaseModel):
    link: str
    updated_at: datetime


class WhatsAppLinkPatchIn(BaseModel):
    link: str | None = Field(default=None)


def _out(obj: WhatsAppLinkConfig) -> WhatsAppLinkOut:
    return WhatsAppLinkOut(link=obj.link, updated_at=obj.updated_at)


@router.get("/whatsapp-link/", response={200: WhatsAppLinkOut}, auth=gated_jwt)
def get_whatsapp_link(request):
    return Status(200, _out(WhatsAppLinkConfig.get()))


@router.patch(
    "/whatsapp-link/",
    response={200: WhatsAppLinkOut, 403: ErrorOut, 422: ErrorOut},
    auth=gated_jwt,
)
def update_whatsapp_link(request, payload: WhatsAppLinkPatchIn):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "update_whatsapp_link",
                "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="edit_whatsapp_link")

    link = (payload.link or "").strip()
    if len(link) > FieldLimit.WHATSAPP_LINK:
        raise_validation(Code.Url.TOO_LONG, field="link", max_length=FieldLimit.WHATSAPP_LINK)
    link = validate_whatsapp_url(link, field="link")

    config = WhatsAppLinkConfig.get()
    config.link = link
    config.save()
    audit_log(
        logging.INFO,
        "whatsapp_link_updated",
        request,
        target_type="whatsapp_link",
    )
    return Status(200, _out(config))
