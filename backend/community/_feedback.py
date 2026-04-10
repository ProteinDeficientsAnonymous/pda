"""Error reporting and GitHub feedback endpoints."""

import json as json_module
import logging
import time
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel, Field

from community._shared import ErrorOut, _optional_jwt

router = Router()

frontend_logger = logging.getLogger("pda.frontend")


class ErrorReportIn(BaseModel):
    error: str = Field(max_length=2000)
    stack_trace: str = Field(default="", max_length=10000)
    context: str = Field(default="", max_length=500)
    route: str = Field(default="", max_length=500)
    user_agent: str = Field(default="", max_length=500)
    app_version: str = Field(default="", max_length=50)
    client_timestamp: str = Field(default="", max_length=50)


class ErrorReportOut(BaseModel):
    detail: str


class FeedbackMetadataIn(BaseModel):
    route: str = Field(default="", max_length=500)
    user_agent: str = Field(default="", max_length=500)
    user_display_name: str = Field(default="", max_length=100)
    user_phone: str = Field(default="", max_length=30)
    app_version: str = Field(default="", max_length=50)


class FeedbackIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    feedback_types: list[str] = Field(default_factory=list)  # "bug", "feature request"
    metadata: FeedbackMetadataIn | None = None


class FeedbackOut(BaseModel):
    html_url: str


@router.post("/error-report/", response={201: ErrorReportOut}, auth=JWTAuth())
def report_error(request, payload: ErrorReportIn):
    extra = {
        k: v
        for k, v in {
            "context": payload.context or "unknown",
            "route": payload.route,
            "user_agent": payload.user_agent,
            "app_version": payload.app_version,
            "client_timestamp": payload.client_timestamp,
        }.items()
        if v
    }
    frontend_logger.error("Frontend error: %s", payload.error, extra=extra)
    if payload.stack_trace:
        frontend_logger.error("Stack trace: %s", payload.stack_trace, extra=extra)
    return Status(201, ErrorReportOut(detail="Error report received."))


def _build_feedback_metadata(meta: FeedbackMetadataIn) -> str:
    lines = ["## Metadata", ""]
    if meta.route:
        lines.append(f"- **Route:** `{meta.route}`")
    if meta.user_agent:
        lines.append(f"- **User Agent:** {meta.user_agent}")
    if meta.user_display_name:
        lines.append(f"- **User:** {meta.user_display_name}")
    if meta.user_phone:
        lines.append(f"- **Phone:** {meta.user_phone}")
    if meta.app_version:
        lines.append(f"- **App Version:** {meta.app_version}")
    return "\n".join(lines) if len(lines) > 2 else ""


def _get_github_app_token(app_id: str, private_key_pem: str, installation_id: str) -> str:
    import jwt as pyjwt

    now = int(time.time())
    app_jwt: str = pyjwt.encode(
        {"iat": now - 60, "exp": now + 540, "iss": app_id},
        private_key_pem,
        algorithm="RS256",
    )
    result = _github_request(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        app_jwt,
        {},
    )
    return result["token"]


def _github_request(url: str, token: str, data: dict) -> dict:
    req = Request(
        url,
        data=json_module.dumps(data).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(req) as response:
        return json_module.loads(response.read())


def _build_issue_body(payload: FeedbackIn, auth_user) -> str:
    parts: list[str] = []

    if payload.description:
        parts.append(payload.description)

    if payload.metadata:
        metadata_section = _build_feedback_metadata(payload.metadata)
        if metadata_section:
            parts.append(metadata_section)

    if not isinstance(auth_user, AnonymousUser):
        parts.append(f"\n_Submitted by {auth_user.display_name or auth_user.phone_number}_")

    return "\n\n".join(parts)


def _issue_labels(feedback_types: list[str]) -> list[str]:
    labels = ["feedback"]
    for t in feedback_types:
        if t == "bug":
            labels.append("bug")
        elif t == "feature request":
            labels.append("enhancement")
    return labels


@router.post(
    "/feedback/",
    response={201: FeedbackOut, 503: ErrorOut},
    auth=_optional_jwt,
)
def submit_feedback(request, payload: FeedbackIn):
    from community._shared import logger

    app_id = settings.GITHUB_APP_ID
    private_key = settings.GITHUB_APP_PRIVATE_KEY
    installation_id = settings.GITHUB_APP_INSTALLATION_ID
    repo = settings.GITHUB_REPO
    logger.info(
        "Feedback submission received: title=%r, app_configured=%s, repo=%r",
        payload.title,
        bool(app_id and private_key and installation_id),
        repo,
    )
    if not all([app_id, private_key, installation_id, repo]):
        logger.warning("Feedback submission rejected: GitHub App not configured")
        return Status(503, ErrorOut(detail="Feedback submission is not configured."))

    issue_body = _build_issue_body(payload, request.auth)

    logger.info("Submitting feedback issue to GitHub repo: %s", repo)
    try:
        token = _get_github_app_token(app_id, private_key, installation_id)
        result = _github_request(
            f"https://api.github.com/repos/{repo}/issues",
            token,
            {
                "title": payload.title,
                "body": issue_body,
                "labels": _issue_labels(payload.feedback_types),
            },
        )
        logger.info("Feedback issue created: %s", result.get("html_url"))
        return Status(201, FeedbackOut(html_url=result["html_url"]))
    except Exception as exc:
        response_body = getattr(exc, "read", lambda: None)()
        logger.exception(
            "Failed to create GitHub issue (status=%s, body=%s)",
            getattr(exc, "code", "unknown"),
            response_body.decode() if response_body else "n/a",
        )
        return Status(503, ErrorOut(detail="Failed to create feedback issue."))
