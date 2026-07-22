import logging

from config.audit import audit_log
from config.auth import gated_jwt
from django.conf import settings
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel
from users.permissions import PermissionKey

from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import FeatureFlag, FeatureFlagState, resolve_flags

router = Router()


class FeatureFlagsOut(BaseModel):
    flags: dict[str, bool]


class FeatureFlagPatchIn(BaseModel):
    enabled: bool


@router.get("/feature-flags/", response={200: FeatureFlagsOut}, auth=None)
def get_feature_flags(request):
    return Status(200, FeatureFlagsOut(flags=resolve_flags()))


@router.patch(
    "/feature-flags/{key}/",
    response={200: FeatureFlagsOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def update_feature_flag(request, key: str, payload: FeatureFlagPatchIn):
    if not settings.FLAG_TOGGLING_ALLOWED:
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={"endpoint": "update_feature_flag", "reason": "prod_environment"},
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_feature_flags")
    if not request.auth.has_permission(PermissionKey.MANAGE_FEATURE_FLAGS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "update_feature_flag",
                "required_permission": PermissionKey.MANAGE_FEATURE_FLAGS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_feature_flags")
    if key not in FeatureFlag.values:
        raise_validation(Code.FeatureFlag.NOT_FOUND, status_code=404)
    state, _ = FeatureFlagState.objects.get_or_create(key=key)
    state.enabled = payload.enabled
    state.save()
    audit_log(
        logging.INFO,
        "feature_flag_updated",
        request,
        target_type="feature_flag",
        target_id=key,
        details={"enabled": payload.enabled},
    )
    return Status(200, FeatureFlagsOut(flags=resolve_flags()))
