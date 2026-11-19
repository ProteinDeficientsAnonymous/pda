"""Users API — merges auth + management sub-routers."""

from ninja import Router

from users._attendance_pause_api import attendance_pause_preview  # re-exported
from users._attendance_pause_api import router as attendance_pause_router
from users._auth import router as auth_router
from users._magic_links import router as magic_links_router
from users._magic_login import router as magic_login_router
from users._management import router as management_router
from users._management import search_users, update_user  # re-exported
from users._members import router as members_router
from users._restored import router as restored_router
from users._roles import router as roles_router
from users._self_delete import router as self_delete_router
from users._user_deletion import router as user_deletion_router
from users.helpers import (  # re-exported
    create_user_with_role,
    validate_admin_role_change,
    validate_member_role_required,
)

__all__ = [
    "create_user_with_role",
    "validate_admin_role_change",
    "validate_member_role_required",
    "attendance_pause_preview",
    "router",
    "search_users",
    "update_user",
]

assert user_deletion_router is management_router
assert attendance_pause_router is management_router

router = Router()
router.add_router("", roles_router)
router.add_router("", auth_router)
router.add_router("", self_delete_router)
router.add_router("", members_router)
router.add_router("", magic_login_router)
router.add_router("", restored_router)
router.add_router("", management_router)
router.add_router("", magic_links_router)
