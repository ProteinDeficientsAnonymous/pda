from ninja_jwt.tokens import RefreshToken
from users.models import User


def auth_headers_for(user: User) -> dict[str, str]:
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}
