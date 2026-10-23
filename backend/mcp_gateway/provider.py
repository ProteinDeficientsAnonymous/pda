from datetime import timedelta
from uuid import UUID

from config.auth import account_block_code
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
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
LAST_USED_RESOLUTION = timedelta(minutes=1)


def _user_may_act(user: User) -> bool:
    return user.is_active and account_block_code(user) is None


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


async def _claim(queryset: QuerySet, pk: UUID, **changes: object) -> bool:
    # Join-free: a joined filter compiles to id IN (subquery), which lets racing claims through.
    return bool(await queryset.filter(pk=pk).aupdate(**changes))


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


async def _revoke_grant_on_refresh_reuse(token_hash: str, client_id: str) -> None:
    # OAuth 2.1 rotation: replaying a rotated refresh token suggests theft, so kill the grant.
    await OAuthGrant.objects.filter(
        tokens__token_hash=token_hash,
        tokens__kind=OAuthToken.Kind.REFRESH,
        tokens__revoked_at__isnull=False,
        client__client_id=client_id,
        revoked_at__isnull=True,
    ).aupdate(revoked_at=timezone.now())


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
        row = await OAuthAuthCode.objects.filter(
            code_hash=hash_secret(authorization_code.code),
            used_at__isnull=True,
            grant__revoked_at__isnull=True,
        ).afirst()
        if row is None or not await _claim(
            OAuthAuthCode.objects.filter(used_at__isnull=True), row.pk, used_at=timezone.now()
        ):
            raise TokenError(error="invalid_grant", error_description="code already used")
        return await _issue_token_pair(row.grant_id, row.scopes, row.resource)

    async def load_access_token(self, token: str) -> AccessToken | None:
        now = timezone.now()
        row = await (
            OAuthToken.objects.select_related("grant__user", "grant__client")
            .filter(
                token_hash=hash_secret(token),
                kind=OAuthToken.Kind.ACCESS,
                revoked_at__isnull=True,
                expires_at__gt=now,
                grant__revoked_at__isnull=True,
            )
            .afirst()
        )
        if row is None or not _user_may_act(row.grant.user):
            return None
        grant = row.grant
        if grant.last_used_at is None or now - grant.last_used_at >= LAST_USED_RESOLUTION:
            await OAuthGrant.objects.filter(pk=grant.pk).aupdate(last_used_at=now)
        return AccessToken(
            token=token,
            client_id=grant.client.client_id,
            scopes=row.scopes,
            expires_at=int(row.expires_at.timestamp()),
            resource=row.resource or None,
            subject=str(grant.user.pk),
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        token_hash = hash_secret(refresh_token)
        row = await (
            OAuthToken.objects.select_related("grant__user")
            .filter(
                token_hash=token_hash,
                kind=OAuthToken.Kind.REFRESH,
                grant__client__client_id=client.client_id,
                grant__revoked_at__isnull=True,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .afirst()
        )
        if row is None:
            await _revoke_grant_on_refresh_reuse(token_hash, client.client_id)
            return None
        if not _user_may_act(row.grant.user):
            return None
        return RefreshToken(
            token=refresh_token,
            client_id=client.client_id,
            scopes=row.scopes,
            expires_at=int(row.expires_at.timestamp()),
            resource=row.resource or None,
            subject=str(row.grant.user.pk),
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> TokenResponse:
        token_hash = hash_secret(refresh_token.token)
        tokens = OAuthToken.objects.filter(
            token_hash=token_hash,
            kind=OAuthToken.Kind.REFRESH,
            revoked_at__isnull=True,
            grant__revoked_at__isnull=True,
        )
        row = await tokens.select_related("grant__user").afirst()
        rejected = TokenError(error="invalid_grant", error_description="refresh token rejected")
        if row is not None and not _user_may_act(row.grant.user):
            raise rejected
        unrevoked = OAuthToken.objects.filter(revoked_at__isnull=True)
        if row is None or not await _claim(unrevoked, row.pk, revoked_at=timezone.now()):
            await _revoke_grant_on_refresh_reuse(token_hash, client.client_id)
            raise rejected
        return await _issue_token_pair(row.grant_id, scopes, row.resource)

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        token_hash, now = hash_secret(token.token), timezone.now()
        if isinstance(token, RefreshToken):
            await OAuthGrant.objects.filter(
                tokens__token_hash=token_hash, revoked_at__isnull=True
            ).aupdate(revoked_at=now)
            return
        await OAuthToken.objects.filter(token_hash=token_hash, revoked_at__isnull=True).aupdate(
            revoked_at=now
        )
