"""Users API — merges auth + management sub-routers."""

from ninja import Router

from users._auth import router as auth_router
from users._helpers import (  # re-exported
    _create_user_with_role,
    _validate_admin_role_change,
    _validate_member_role_required,
)
from users._magic_links import router as magic_links_router
from users._management import router as management_router
from users._roles import router as roles_router

__all__ = [
    "_create_user_with_role",
    "_validate_admin_role_change",
    "_validate_member_role_required",
    "router",
]

router = Router()
router.add_router("", roles_router)
router.add_router("", auth_router)
router.add_router("", management_router)
router.add_router("", magic_links_router)
