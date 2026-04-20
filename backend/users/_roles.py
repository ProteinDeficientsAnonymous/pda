"""Role management endpoints."""

import logging

from config.audit import audit_log
from django.db.models import Count, Q
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth

from users.permissions import PermissionKey
from users.roles import PROTECTED_ROLE_NAMES, Role
from users.schemas import ErrorOut, RoleIn, RoleOut, RolePatchIn

router = Router()


@router.get("/roles/", response={200: list[RoleOut]}, auth=JWTAuth())
def list_roles(request):
    roles = Role.objects.annotate(
        user_count=Count("users", filter=Q(users__archived_at__isnull=True)),
    )
    return Status(
        200,
        [
            RoleOut(
                id=str(r.id),
                name=r.name,
                is_default=r.is_default,
                permissions=r.effective_permissions,
                user_count=r.user_count,
            )
            for r in roles
        ],
    )


@router.post(
    "/roles/",
    response={201: RoleOut, 400: ErrorOut, 403: ErrorOut},
    auth=JWTAuth(),
)
def create_role(request, payload: RoleIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_ROLES):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={"endpoint": "create_role", "required_permission": PermissionKey.MANAGE_ROLES},
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    if Role.objects.filter(name=payload.name).exists():
        return Status(400, ErrorOut(detail="A role with that name already exists."))
    role = Role.objects.create(name=payload.name, permissions=payload.permissions)
    audit_log(
        logging.INFO,
        "role_created",
        request,
        target_type="role",
        target_id=str(role.id),
        details={"name": role.name, "permissions": role.permissions},
    )
    return Status(
        201,
        RoleOut(
            id=str(role.id),
            name=role.name,
            is_default=role.is_default,
            permissions=role.permissions,
        ),
    )


@router.patch(
    "/roles/{role_id}/",
    response={200: RoleOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_role(request, role_id: str, payload: RolePatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_ROLES):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="role",
            target_id=role_id,
            details={"endpoint": "update_role", "required_permission": PermissionKey.MANAGE_ROLES},
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        role = Role.objects.get(pk=role_id)
    except Role.DoesNotExist:
        return Status(404, ErrorOut(detail="Role not found."))

    if role.is_default:
        return Status(400, ErrorOut(detail=f"Cannot edit the built-in '{role.name}' role."))

    old_name = role.name
    old_permissions = list(role.permissions)

    if payload.name is not None and payload.name != role.name:
        if role.name in PROTECTED_ROLE_NAMES:
            return Status(400, ErrorOut(detail=f"Cannot rename protected role '{role.name}'."))
        if Role.objects.exclude(pk=role_id).filter(name=payload.name).exists():
            return Status(400, ErrorOut(detail="A role with that name already exists."))
        role.name = payload.name

    if payload.permissions is not None:
        role.permissions = payload.permissions

    role.save()
    audit_log(
        logging.WARNING,
        "role_updated",
        request,
        target_type="role",
        target_id=role_id,
        details={
            "old_name": old_name,
            "new_name": role.name,
            "old_permissions": old_permissions,
            "new_permissions": role.permissions,
        },
    )
    return Status(
        200,
        RoleOut(
            id=str(role.id),
            name=role.name,
            is_default=role.is_default,
            permissions=role.permissions,
        ),
    )


@router.delete(
    "/roles/{role_id}/",
    response={204: None, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_role(request, role_id: str):
    if not request.auth.has_permission(PermissionKey.MANAGE_ROLES):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="role",
            target_id=role_id,
            details={"endpoint": "delete_role", "required_permission": PermissionKey.MANAGE_ROLES},
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        role = Role.objects.get(pk=role_id)
    except Role.DoesNotExist:
        return Status(404, ErrorOut(detail="Role not found."))
    if role.name in PROTECTED_ROLE_NAMES:
        return Status(400, ErrorOut(detail=f"Cannot delete protected role '{role.name}'."))
    role_name = role.name
    affected_user_count = role.users.filter(archived_at__isnull=True).count()
    role.delete()
    audit_log(
        logging.WARNING,
        "role_deleted",
        request,
        target_type="role",
        target_id=role_id,
        details={"name": role_name, "affected_user_count": affected_user_count},
    )
    return Status(204, None)
