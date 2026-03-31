from django.conf import settings
from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel
from stream_chat import StreamChat  # type: ignore[import-untyped]

router = Router()


class StreamTokenOut(BaseModel):
    token: str
    api_key: str
    user_id: str


def _get_client() -> StreamChat:
    if not settings.STREAM_CHAT_API_KEY or not settings.STREAM_CHAT_API_SECRET:
        raise HttpError(503, "Chat is not configured.")
    return StreamChat(
        api_key=settings.STREAM_CHAT_API_KEY,
        api_secret=settings.STREAM_CHAT_API_SECRET,
    )


@router.get("/token/", auth=JWTAuth(), response=StreamTokenOut)
def get_stream_token(request):
    """Return a Stream Chat token for the authenticated user.

    Also upserts the user in Stream so their display name stays in sync.
    """
    client = _get_client()
    user = request.auth
    user_id = str(user.pk)
    display_name = user.display_name or user.phone_number

    client.upsert_user({"id": user_id, "name": display_name})
    token = client.create_token(user_id)

    return StreamTokenOut(
        token=token,
        api_key=settings.STREAM_CHAT_API_KEY,
        user_id=user_id,
    )
