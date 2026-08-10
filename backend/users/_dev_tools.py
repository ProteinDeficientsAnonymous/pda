import logging
import os

from community._validation import Code, raise_validation
from community.management.commands._seed_staging_data import is_seed_allowed
from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field

from users._helpers import _normalize_email
from users.models import ADMIN_ENTERED_PHONE_REGION, User, validate_phone
from users.permissions import PermissionKey
from users.schemas import ErrorOut

router = Router()

DEFAULT_DEV_PASSWORD = "testPassword1@"  # noqa: S105 — dev-only tool, non-prod gated


class DevTestUserIn(BaseModel):
    first_name: str = Field(default="Test", max_length=64)
    last_name: str = Field(default="User", max_length=64)
    password: str = Field(default=DEFAULT_DEV_PASSWORD, min_length=8, max_length=128)
    is_member: bool = True
    needs_onboarding: bool = False
    needs_password_reset: bool = False
    is_paused: bool = False
    is_archived: bool = False
    guidelines_consent: bool = True
    sms_consent: bool = True
    contact_privacy_consent: bool = True


class DevTestUserOut(BaseModel):
    id: str
    phone_number: str
    first_name: str
    last_name: str
    password: str


def _require_dev_tools(request) -> None:
    if not is_seed_allowed(os.environ.get("RAILWAY_ENVIRONMENT_NAME"), force=False):
        raise_validation(Code.DevTools.NOT_FOUND, status_code=404)
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        raise_validation(Code.DevTools.NOT_FOUND, status_code=404)


@router.post(
    "/dev/test-users/",
    response={201: DevTestUserOut, 404: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/h")
def create_dev_test_user(request, payload: DevTestUserIn):
    _require_dev_tools(request)

    now = timezone.now()
    # 702-555-XXXX: real area code + fictional exchange, matches seed data's test numbers.
    suffix = str(int(now.timestamp() * 1000))[-4:]
    phone_number = validate_phone(f"+1702555{suffix}", ADMIN_ENTERED_PHONE_REGION)
    email = _normalize_email(f"dev-test-{now.timestamp()}@example.com")

    user = User.objects.create_user(
        phone_number=phone_number,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=email,
        is_member=payload.is_member,
        needs_onboarding=payload.needs_onboarding,
        needs_password_reset=payload.needs_password_reset,
        is_paused=payload.is_paused,
        archived_at=now if payload.is_archived else None,
        guidelines_consent_at=now if payload.guidelines_consent else None,
        sms_consent_at=now if payload.sms_consent else None,
        contact_privacy_consent_at=now if payload.contact_privacy_consent else None,
    )

    audit_log(
        logging.INFO,
        "dev_test_user_created",
        request,
        target=AuditTarget(type=AuditTargetType.USER, id=str(user.id)),
    )
    return Status(
        201,
        DevTestUserOut(
            id=str(user.id),
            phone_number=user.phone_number,
            first_name=user.first_name,
            last_name=user.last_name,
            password=payload.password,
        ),
    )
