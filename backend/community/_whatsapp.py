"""WhatsApp configuration endpoints."""

import logging

from config.audit import audit_log
from django.conf import settings
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from community._field_limits import FieldLimit
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import WhatsAppConfig

router = Router()


class WhatsAppConfigOut(BaseModel):
    bot_url: str
    group_id: str
    has_secret: bool  # Don't expose the secret value, just whether it's set


class WhatsAppConfigPatchIn(BaseModel):
    bot_url: str | None = Field(default=None, max_length=FieldLimit.URL)
    bot_secret: str | None = Field(default=None, max_length=FieldLimit.BOT_SECRET)
    group_id: str | None = Field(default=None, max_length=FieldLimit.BOT_SECRET)


class WhatsAppStatusOut(BaseModel):
    connected: bool


@router.get(
    "/whatsapp/config/",
    response={200: WhatsAppConfigOut, 403: ErrorOut},
    auth=JWTAuth(),
)
def get_whatsapp_config(request):
    if not request.auth.has_permission(PermissionKey.MANAGE_WHATSAPP):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "get_whatsapp_config",
                "required_permission": PermissionKey.MANAGE_WHATSAPP,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_whatsapp")
    config = WhatsAppConfig.get()
    return Status(
        200,
        WhatsAppConfigOut(
            bot_url=config.bot_url,
            group_id=config.group_id,
            has_secret=bool(config.bot_secret),
        ),
    )


@router.patch(
    "/whatsapp/config/",
    response={200: WhatsAppConfigOut, 403: ErrorOut},
    auth=JWTAuth(),
)
def update_whatsapp_config(request, payload: WhatsAppConfigPatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_WHATSAPP):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "update_whatsapp_config",
                "required_permission": PermissionKey.MANAGE_WHATSAPP,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_whatsapp")
    config = WhatsAppConfig.get()
    changed = []
    if payload.bot_url is not None:
        config.bot_url = payload.bot_url
        changed.append("bot_url")
    if payload.bot_secret is not None:
        config.bot_secret = payload.bot_secret
        changed.append("bot_secret")  # log field name only, never the value
    if payload.group_id is not None:
        config.group_id = payload.group_id
        changed.append("group_id")
    config.save()
    audit_log(
        logging.WARNING,
        "whatsapp_config_updated",
        request,
        target_type="whatsapp_config",
        details={"fields_changed": changed},
    )
    return Status(
        200,
        WhatsAppConfigOut(
            bot_url=config.bot_url,
            group_id=config.group_id,
            has_secret=bool(config.bot_secret),
        ),
    )


@router.get(
    "/whatsapp/status/",
    response={200: WhatsAppStatusOut, 403: ErrorOut},
    auth=JWTAuth(),
)
def get_whatsapp_status(request):
    if not request.auth.has_permission(PermissionKey.MANAGE_WHATSAPP):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "get_whatsapp_status",
                "required_permission": PermissionKey.MANAGE_WHATSAPP,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_whatsapp")
    config = WhatsAppConfig.get()
    bot_url = config.bot_url or getattr(settings, "WHATSAPP_BOT_URL", "")
    if not bot_url:
        return Status(200, WhatsAppStatusOut(connected=False))
    try:
        import urllib.request as _urllib

        req = _urllib.Request(
            bot_url.rstrip("/") + "/status",
            headers={
                "X-Bot-Secret": config.bot_secret or getattr(settings, "WHATSAPP_BOT_SECRET", "")
            },
        )
        with _urllib.urlopen(req, timeout=5) as resp:
            import json as _json

            data = _json.loads(resp.read())
            return Status(200, WhatsAppStatusOut(connected=bool(data.get("connected"))))
    except Exception:
        return Status(200, WhatsAppStatusOut(connected=False))
