"""Error reporting and GitHub feedback endpoints."""

import json as json_module
import logging
import time
from urllib.request import Request, urlopen

from config.auth import gated_jwt
from config.ratelimit import client_ip, rate_limit
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field

from community._shared import ErrorOut, _optional_jwt
from community._validation import Code, raise_validation

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
    app_version: str = Field(default="", max_length=50)


class FeedbackIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    feedback_types: list[str] = Field(default_factory=list)  # "bug", "feature request"
    metadata: FeedbackMetadataIn | None = None


class FeedbackOut(BaseModel):
    html_url: str


@router.post("/error-report/", response={201: ErrorReportOut}, auth=gated_jwt)
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


def _inline_code(value: str) -> str:
    """Render untrusted text as a GitHub inline-code span, escaping any
    backticks so the value can't break out into active markdown."""
    cleaned = " ".join(value.splitlines()).replace("`", "'")
    return f"`{cleaned}`"


def _fenced_block(value: str) -> str:
    """Wrap untrusted multi-line text in a fenced code block so markdown,
    @mentions, and #issue-refs inside it render inert. The fence is sized
    longer than the longest backtick run in the content so the user can't
    close the fence early."""
    longest_run = 0
    current = 0
    for ch in value:
        if ch == "`":
            current += 1
            longest_run = max(longest_run, current)
        else:
            current = 0
    fence = "`" * max(3, longest_run + 1)
    return f"{fence}\n{value}\n{fence}"


def _build_feedback_metadata(meta: FeedbackMetadataIn) -> str:
    lines = ["## Metadata", ""]
    if meta.route:
        lines.append(f"- **Route:** {_inline_code(meta.route)}")
    if meta.user_agent:
        lines.append(f"- **User Agent:** {_inline_code(meta.user_agent)}")
    if meta.app_version:
        lines.append(f"- **App Version:** {_inline_code(meta.app_version)}")
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
        # User-supplied free text — fence it so markdown, @mentions, and
        # #issue-refs render inert in the GitHub issue.
        parts.append(_fenced_block(payload.description))

    if payload.metadata:
        metadata_section = _build_feedback_metadata(payload.metadata)
        if metadata_section:
            parts.append(metadata_section)

    if not isinstance(auth_user, AnonymousUser):
        parts.append(f"\n_Submitted by user id: `{auth_user.id}`_")

    return "\n\n".join(parts)


def _issue_labels(feedback_types: list[str]) -> list[str]:
    labels = ["feedback"]
    for t in feedback_types:
        if t == "bug":
            labels.append("bug")
        elif t == "feature request":
            labels.append("enhancement")
    return labels


def _feedback_key(request) -> str:
    """Key feedback submissions by authed user when possible, else client IP."""
    pk = getattr(request.auth, "pk", None)
    return str(pk) if pk is not None else client_ip(request)


@router.post(
    "/feedback/",
    response={201: FeedbackOut, 429: ErrorOut, 503: ErrorOut},
    auth=_optional_jwt,
)
@rate_limit(key_func=_feedback_key, rate="5/h")
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
        raise_validation(Code.Feedback.NOT_CONFIGURED, status_code=503)

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
        raise_validation(Code.Feedback.CREATION_FAILED, status_code=503)
