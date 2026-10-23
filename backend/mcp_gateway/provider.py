from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    TokenError,
)
from mcp.shared.auth import OAuthClientInformationFull
from mcp.shared.auth import OAuthToken as TokenResponse
from users.models import User

from mcp_gateway.models import (
    OAuthAuthCode,
    OAuthAuthRequest,
    OAuthClient,
    OAuthGrant,
    OAuthToken,
)
from mcp_gateway.tokens import (
    ACCESS_TTL,
    AUTH_CODE_TTL,
    AUTH_REQUEST_TTL,
    REFRESH_TTL,
    hash_secret,
    new_secret,
)

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


async def _issue_token_pair(grant_id: UUID, scopes: list[str], resource: str) -> TokenResponse:
    now = timezone.now()
    access, refresh = new_secret(), new_secret()
    await OAuthToken.objects.abulk_create(
        [
            OAuthToken(
                token_hash=hash_secret(secret),
                kind=kind,
                grant_id=grant_id,
                scopes=scopes,
                resource=resource,
                expires_at=now + ttl,
            )
            for secret, kind, ttl in (
                (access, OAuthToken.Kind.ACCESS, ACCESS_TTL),
                (refresh, OAuthToken.Kind.REFRESH, REFRESH_TTL),
            )
        ]
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=int(ACCESS_TTL.total_seconds()),
        scope=" ".join(scopes),
    )


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

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        row = await (
            OAuthAuthCode.objects.select_related("grant")
            .filter(
                code_hash=hash_secret(authorization_code),
                grant__client__client_id=client.client_id,
                grant__revoked_at__isnull=True,
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .afirst()
        )
        if row is None:
            return None
        return AuthorizationCode(
            code=authorization_code,
            scopes=row.scopes,
            expires_at=row.expires_at.timestamp(),
            client_id=client.client_id,
            code_challenge=row.code_challenge,
            redirect_uri=row.redirect_uri,
            redirect_uri_provided_explicitly=row.redirect_uri_provided_explicitly,
            resource=row.resource or None,
            subject=str(row.grant.user_id),
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> TokenResponse:
        codes = OAuthAuthCode.objects.filter(
            code_hash=hash_secret(authorization_code.code),
            used_at__isnull=True,
            grant__revoked_at__isnull=True,
        )
        row = await codes.afirst()
        # The conditional update is the single-use claim; a concurrent exchange gets 0 rows.
        if row is None or not await codes.filter(pk=row.pk).aupdate(used_at=timezone.now()):
            raise TokenError(error="invalid_grant", error_description="code already used")
        return await _issue_token_pair(row.grant_id, row.scopes, row.resource)
