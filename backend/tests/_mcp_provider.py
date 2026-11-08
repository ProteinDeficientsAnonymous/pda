from asgiref.sync import async_to_sync
from mcp.server.auth.provider import AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull
from mcp.shared.auth import OAuthToken as TokenResponse
from mcp_gateway.models import OAuthAuthRequest
from mcp_gateway.provider import PdaOAuthProvider, issue_auth_code

from tests._mcp_helpers import REDIRECT

RESOURCE = "https://pda.test/mcp"


def client_info(client_id: str = "client-1") -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        client_name="claude",
        redirect_uris=[REDIRECT],
        token_endpoint_auth_method="none",
        scope="pda",
    )


def auth_params(scopes: list[str] | None = None) -> AuthorizationParams:
    return AuthorizationParams(
        state="xyz",
        scopes=scopes,
        code_challenge="challenge",
        redirect_uri=REDIRECT,
        redirect_uri_provided_explicitly=True,
        resource=RESOURCE,
    )


def pending_request(provider: PdaOAuthProvider) -> OAuthAuthRequest:
    info = client_info()
    async_to_sync(provider.register_client)(info)
    url = async_to_sync(provider.authorize)(info, auth_params())
    return OAuthAuthRequest.objects.get(pk=url.rsplit("=", 1)[1])


def connect_client(provider: PdaOAuthProvider, user) -> TokenResponse:
    code = issue_auth_code(pending_request(provider), user)
    loaded = async_to_sync(provider.load_authorization_code)(client_info(), code)
    assert loaded is not None
    return async_to_sync(provider.exchange_authorization_code)(client_info(), loaded)
