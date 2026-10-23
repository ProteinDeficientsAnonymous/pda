import logging
from typing import NoReturn
from urllib.parse import urlparse
from uuid import UUID

from audit.models import AuditTargetType
from community._validation import Code, raise_validation
from config.audit import AuditTarget, audit_log
from config.auth import gated_jwt
from django.utils import timezone
from mcp.server.auth.provider import construct_redirect_uri
from ninja import Router
from ninja.responses import Status

from mcp_gateway.models import OAuthAuthCode, OAuthAuthRequest
from mcp_gateway.provider import AuthRequestNotPending, issue_auth_code
from mcp_gateway.schemas import ConnectRedirectOut, ConnectRequestOut
from mcp_gateway.tokens import hash_secret

router = Router()


def _raise_unusable(auth_request_id: UUID) -> NoReturn:
    row = OAuthAuthRequest.objects.filter(pk=auth_request_id).first()
    if row is None:
        raise_validation(Code.Connect.REQUEST_NOT_FOUND, status_code=404)
    if row.status == OAuthAuthRequest.Status.PENDING and row.expires_at <= timezone.now():
        raise_validation(Code.Connect.REQUEST_EXPIRED, status_code=410)
    raise_validation(Code.Connect.REQUEST_ALREADY_USED, status_code=409)


def _get_pending_request(request_id: UUID) -> OAuthAuthRequest:
    row = OAuthAuthRequest.objects.select_related("client").filter(pk=request_id).first()
    if (
        row is None
        or row.status != OAuthAuthRequest.Status.PENDING
        or row.expires_at <= timezone.now()
    ):
        _raise_unusable(request_id)
    return row


@router.get("/requests/{request_id}/", response={200: ConnectRequestOut}, auth=gated_jwt)
def get_request(request, request_id: UUID):
    row = _get_pending_request(request_id)
    return Status(
        200,
        ConnectRequestOut(
            client_name=row.client.client_name,
            redirect_host=urlparse(row.params["redirect_uri"]).hostname or "",
            expires_at=row.expires_at,
        ),
    )


@router.post("/requests/{request_id}/approve/", response={200: ConnectRedirectOut}, auth=gated_jwt)
def approve_request(request, request_id: UUID):
    row = _get_pending_request(request_id)
    try:
        code = issue_auth_code(row, request.auth)
    except AuthRequestNotPending:
        _raise_unusable(request_id)
    grant_id = OAuthAuthCode.objects.values_list("grant_id", flat=True).get(
        code_hash=hash_secret(code)
    )
    audit_log(
        logging.INFO,
        "mcp_connection_approved",
        request,
        target=AuditTarget(type=AuditTargetType.MCP_CONNECTION, id=str(grant_id)),
    )
    redirect_url = construct_redirect_uri(
        row.params["redirect_uri"], code=code, state=row.params.get("state")
    )
    return Status(200, ConnectRedirectOut(redirect_url=redirect_url))
