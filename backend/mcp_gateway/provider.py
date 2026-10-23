from django.conf import settings
from django.db import transaction
from django.utils import timezone
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
)
from mcp.shared.auth import OAuthClientInformationFull
from users.models import User

from mcp_gateway.models import OAuthAuthCode, OAuthAuthRequest, OAuthClient, OAuthGrant
from mcp_gateway.tokens import AUTH_CODE_TTL, AUTH_REQUEST_TTL, hash_secret, new_secret

SCOPE = "pda"


class AuthRequestNotPending(Exception):
    pass


@transaction.atomic
def issue_auth_code(auth_request: OAuthAuthRequest, user: User) -> str:
    now = timezone.now()
    claimed = OAuthAuthRequest.objects.filter(
        pk=auth_request.pk, status=OAuthAuthRequest.Status.PENDING, expires_at__gt=now
    ).update(status=OAuthAuthRequest.Status.APPROVED, user=user)
    if not claimed:
        raise AuthRequestNotPending
    auth_request.status = OAuthAuthRequest.Status.APPROVED
    auth_request.user = user

    params = AuthorizationParams.model_validate(auth_request.params)
    grant = OAuthGrant.objects.create(user=user, client=auth_request.client)
    code = new_secret()
    OAuthAuthCode.objects.create(
        code_hash=hash_secret(code),
        grant=grant,
        scopes=params.scopes or [SCOPE],
        code_challenge=params.code_challenge,
        redirect_uri=str(params.redirect_uri),
        redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
        resource=params.resource or "",
        expires_at=now + AUTH_CODE_TTL,
    )
    return code


class PdaOAuthProvider(
    OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]
):
    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        row = await OAuthClient.objects.filter(client_id=client_id).afirst()
        return OAuthClientInformationFull.model_validate(row.info) if row else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        await OAuthClient.objects.acreate(
            client_id=client_info.client_id,
            client_name=client_info.client_name or "",
            info=client_info.model_dump(mode="json"),
        )

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        row = await OAuthClient.objects.aget(client_id=client.client_id)
        req = await OAuthAuthRequest.objects.acreate(
            client=row,
            params=params.model_dump(mode="json"),
            expires_at=timezone.now() + AUTH_REQUEST_TTL,
        )
        return f"{settings.FRONTEND_BASE_URL}/connect/authorize?request={req.id}"
