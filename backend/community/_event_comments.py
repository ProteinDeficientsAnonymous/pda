"""EventComment endpoints — list, post, reply, delete, react."""

from uuid import UUID

from config.media_proxy import media_path
from config.ratelimit import rate_limit
from django.db import transaction
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from users.permissions import PermissionKey

from community._event_comment_schemas import (
    CommentBodyIn,
    CommentReactionSummaryOut,
    EventCommentListOut,
    EventCommentOut,
    EventCommentReplyOut,
)
from community._events import _enforce_event_read_visibility
from community._shared import ErrorOut, _authenticated_user, _optional_jwt
from community._validation import Code, raise_validation
from community.models import (
    Event,
    EventComment,
    EventCommentReaction,
    EventRSVP,
)

router = Router()


# ---------- helpers ----------


def _viewer_has_rsvp(event: Event, user) -> bool:
    if user is None:
        return False
    return EventRSVP.objects.filter(event=event, user=user).exists()


def _can_delete_comment(event: Event, comment: EventComment, user) -> bool:
    """Authors can always delete their own; creator / co-host / MANAGE_EVENTS can delete others'."""
    if user is None:
        return False
    if comment.author_id == user.pk:
        return True
    if user.has_permission(PermissionKey.MANAGE_EVENTS):
        return True
    if event.created_by_id == user.pk:
        return True
    return event.co_hosts.filter(pk=user.pk).exists()


def _reactions_summary(
    reactions: list[EventCommentReaction], viewer_id
) -> list[CommentReactionSummaryOut]:
    """Aggregate prefetched reactions into per-emoji counts + reacted_by_me."""
    by_emoji: dict[str, dict] = {}
    for r in reactions:
        bucket = by_emoji.setdefault(r.emoji, {"count": 0, "reacted_by_me": False})
        bucket["count"] += 1
        if viewer_id is not None and str(r.user_id) == str(viewer_id):
            bucket["reacted_by_me"] = True
    return [
        CommentReactionSummaryOut(emoji=e, count=v["count"], reacted_by_me=v["reacted_by_me"])
        for e, v in by_emoji.items()
    ]


def _safe_photo_url(user) -> str:
    """Match the codebase pattern of media_path() returning '' for falsy profile_photo."""
    return media_path(user.profile_photo)


def _comment_reply_out(comment: EventComment, event: Event, viewer) -> EventCommentReplyOut:
    is_deleted = comment.deleted_at is not None
    reactions = (
        []
        if is_deleted
        else _reactions_summary(
            list(comment.reactions.all()),
            viewer.pk if viewer else None,
        )
    )
    return EventCommentReplyOut(
        id=str(comment.id),
        author_id=str(comment.author_id),
        author_display_name=comment.author.display_name or comment.author.phone_number,
        author_photo_url=_safe_photo_url(comment.author),
        body="" if is_deleted else comment.body,
        is_deleted=is_deleted,
        created_at=comment.created_at,
        reactions=reactions,
        can_delete=_can_delete_comment(event, comment, viewer),
    )


def _comment_out(comment: EventComment, event: Event, viewer) -> EventCommentOut:
    reply_list = sorted(comment.replies.all(), key=lambda r: r.created_at)
    base = _comment_reply_out(comment, event, viewer)
    return EventCommentOut(
        **base.model_dump(),
        replies=[_comment_reply_out(r, event, viewer) for r in reply_list],
    )


def _build_list_out(event: Event, viewer) -> EventCommentListOut:
    comments = (
        EventComment.objects.filter(event=event, parent__isnull=True)
        .select_related("author")
        .prefetch_related("replies__author", "reactions", "replies__reactions")
        .order_by("-created_at")
    )
    can_post = viewer is not None and _viewer_has_rsvp(event, viewer)
    if viewer is None:
        reason: str | None = "login_required"
    elif not can_post:
        reason = "rsvp_required"
    else:
        reason = None
    return EventCommentListOut(
        items=[_comment_out(c, event, viewer) for c in comments],
        can_post=can_post,
        cannot_post_reason=reason,
    )


def _require_rsvp_for_post(event: Event, user) -> None:
    if not _viewer_has_rsvp(event, user):
        raise_validation(Code.Comment.RSVP_REQUIRED, status_code=403)


# ---------- endpoints ----------


@router.get(
    "/events/{event_id}/comments/",
    response={200: EventCommentListOut, 404: ErrorOut, 403: ErrorOut},
    auth=_optional_jwt,
)
def list_comments(request, event_id: UUID):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    auth_user = _authenticated_user(request.auth)
    _enforce_event_read_visibility(event, auth_user)
    return Status(200, _build_list_out(event, auth_user))


@router.post(
    "/events/{event_id}/comments/",
    response={201: EventCommentOut, 403: ErrorOut, 404: ErrorOut, 422: ErrorOut, 429: ErrorOut},
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/m")
def post_comment(request, event_id: UUID, payload: CommentBodyIn):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    user = request.auth
    _enforce_event_read_visibility(event, user)
    _require_rsvp_for_post(event, user)
    with transaction.atomic():
        comment = EventComment.objects.create(event=event, author=user, body=payload.body)
    return Status(201, _comment_out(comment, event, user))
