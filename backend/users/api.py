from ninja import Router
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_jwt.tokens import RefreshToken
from pydantic import BaseModel

from users.models import User

router = Router()


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access: str
    refresh: str


class RefreshIn(BaseModel):
    refresh: str


class AccessOut(BaseModel):
    access: str


class UserOut(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str

    @classmethod
    def from_user(cls, user: User) -> "UserOut":
        return cls(
            id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
        )


class ErrorOut(BaseModel):
    detail: str


@router.post("/login/", response={200: TokenOut, 401: ErrorOut}, auth=None)
def login(request, payload: LoginIn):
    from django.contrib.auth import authenticate

    user = authenticate(request, username=payload.email, password=payload.password)
    if user is None:
        return 401, ErrorOut(detail="Invalid credentials")
    refresh = RefreshToken.for_user(user)
    return 200, TokenOut(access=str(refresh.access_token), refresh=str(refresh))


@router.post("/refresh/", response={200: AccessOut, 401: ErrorOut}, auth=None)
def refresh_token(request, payload: RefreshIn):
    try:
        refresh = RefreshToken(payload.refresh)
        return 200, AccessOut(access=str(refresh.access_token))
    except Exception:
        return 401, ErrorOut(detail="Invalid or expired refresh token")


@router.get("/me/", response={200: UserOut, 401: ErrorOut}, auth=JWTAuth())
def me(request):
    return 200, UserOut.from_user(request.auth)
