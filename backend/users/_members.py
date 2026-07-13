from community._validation import Code, raise_validation
from config.auth import gated_jwt
from config.media_proxy import media_path
from ninja import Router
from ninja.responses import Status

from users._helpers import visible_display_name, visible_name
from users.models import User
from users.permissions import PermissionKey
from users.schemas import (
    ErrorOut,
    MemberDirectoryOut,
    MemberProfileOut,
)

router = Router()


@router.get(
    "/users/directory/",
    response={200: list[MemberDirectoryOut]},
    auth=gated_jwt,
)
def list_member_directory(request):
    """Authed-only member directory. Respects each user's show_phone/show_email flags."""
    users = (
        User.objects.active_members()
        .filter(needs_onboarding=False)
        .order_by("display_name", "phone_number")
    )
    results = []
    for u in users:
        last_name, full_name = visible_name(u, request.auth)
        results.append(
            MemberDirectoryOut(
                id=str(u.id),
                display_name=visible_display_name(u, request.auth),
                first_name=u.first_name,
                last_name=last_name,
                full_name=full_name,
                phone_number=u.phone_number if u.show_phone else "",
                email=(u.email or "") if u.show_email else "",
                profile_photo_url=media_path(u.profile_photo),
            )
        )
    return Status(200, results)


@router.get(
    "/users/{user_id}/profile/",
    response={200: MemberProfileOut, 404: ErrorOut},
    auth=gated_jwt,
)
def get_member_profile(request, user_id: str):
    try:
        user = User.objects.active_members().get(pk=user_id)
    except User.DoesNotExist:
        raise_validation(Code.Member.NOT_FOUND, status_code=404)
    is_own_profile = str(request.auth.pk) == user_id
    can_manage_users = request.auth.has_permission(PermissionKey.MANAGE_USERS)
    last_name, full_name = visible_name(user, request.auth)
    return Status(
        200,
        MemberProfileOut(
            id=str(user.id),
            display_name=visible_display_name(user, request.auth),
            first_name=user.first_name,
            last_name=last_name,
            full_name=full_name,
            nickname=user.nickname or "",
            phone_number=user.phone_number if (user.show_phone or is_own_profile) else "",
            email=(user.email or "") if (user.show_email or is_own_profile) else "",
            bio=user.bio or "",
            pronouns=user.pronouns or "",
            profile_photo_url=media_path(user.profile_photo),
            login_link_requested=user.login_link_requested if can_manage_users else False,
        ),
    )
