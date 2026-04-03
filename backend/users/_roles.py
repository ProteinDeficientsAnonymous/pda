"""Role management endpoints."""

from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth

from users.permissions import PermissionKey
from users.roles import PROTECTED_ROLE_NAMES, Role
from users.schemas import ErrorOut, RoleIn, RoleOut, RolePatchIn

router = Router()


@router.get("/roles/", response={200: list[RoleOut]}, auth=JWTAuth())
def list_roles(request):
    roles = Role.objects.all()
    return Status(
        200,
        [
            RoleOut(id=str(r.id), name=r.name, is_default=r.is_default, permissions=r.permissions)
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
        return Status(403, ErrorOut(detail="Permission denied."))
    if Role.objects.filter(name=payload.name).exists():
        return Status(400, ErrorOut(detail="A role with that name already exists."))
    role = Role.objects.create(name=payload.name, permissions=payload.permissions)
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
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        role = Role.objects.get(pk=role_id)
    except Role.DoesNotExist:
        return Status(404, ErrorOut(detail="Role not found."))

    if payload.name is not None and payload.name != role.name:
        if role.name in PROTECTED_ROLE_NAMES:
            return Status(400, ErrorOut(detail=f"Cannot rename protected role '{role.name}'."))
        if Role.objects.exclude(pk=role_id).filter(name=payload.name).exists():
            return Status(400, ErrorOut(detail="A role with that name already exists."))
        role.name = payload.name

    if payload.permissions is not None:
        role.permissions = payload.permissions

    role.save()
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
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        role = Role.objects.get(pk=role_id)
    except Role.DoesNotExist:
        return Status(404, ErrorOut(detail="Role not found."))
    if role.name in PROTECTED_ROLE_NAMES:
        return Status(400, ErrorOut(detail=f"Cannot delete protected role '{role.name}'."))
    if role.users.exists():
        return Status(400, ErrorOut(detail="Cannot delete a role that has users assigned."))
    role.delete()
    return Status(204, None)
