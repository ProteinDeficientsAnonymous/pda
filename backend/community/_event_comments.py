"""EventComment endpoints — list, post, reply, delete, react."""

from uuid import UUID

from config.media_proxy import media_path
from config.ratelimit import client_ip, rate_limit
from django.db import transaction
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from notifications.service import (
    broadcast_event_update,
    notify_comment_reply,
    notify_event_comment,
)
from users._helpers import visible_display_name
from users.permissions import PermissionKey

from community._event_comment_schemas import (
    CommentBodyIn,
    CommentReactionSummaryOut,
    EventCommentListOut,
    EventCommentOut,
    EventCommentReplyOut,
    ReactionToggleIn,
)
from community._event_viewer import resolve_event_viewer
from community._events import _enforce_event_read_visibility
from community._shared import ErrorOut, _optional_jwt
from community._validation import Code, raise_validation
from community.models import (
    Event,
    EventComment,
    EventCommentReaction,
    EventRSVP,
    ReactionEmoji,
)

router = Router()


# ---------- helpers ----------


def _viewer_has_rsvp(event: Event, user) -> bool:
    if user is None:
        return False
    return EventRSVP.objects.filter(event=event, user=user).exists()


def _can_post_comments(
    event: Event,
    user,
    co_host_pks: set[str] | None = None,
) -> bool:
    """Posting requires either an RSVP or host/admin privilege on the event."""
    if user is None:
        return False
    if user.has_permission(PermissionKey.MANAGE_EVENTS):
        return True
    if event.created_by_id == user.pk:
        return True
    if co_host_pks is not None:
        if str(user.pk) in co_host_pks:
            return True
    elif event.co_hosts.filter(pk=user.pk).exists():
        return True
    return _viewer_has_rsvp(event, user)


def _can_delete_comment(
    event: Event,
    comment: EventComment,
    user,
    co_host_pks: set[str] | None = None,
) -> bool:
    """Authors can always delete their own; creator / co-host / MANAGE_EVENTS can delete others'."""
    if user is None:
        return False
    if comment.author_id == user.pk:
        return True
    if user.has_permission(PermissionKey.MANAGE_EVENTS):
        return True
    if event.created_by_id == user.pk:
        return True
    if co_host_pks is not None:
        return str(user.pk) in co_host_pks
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


def _comment_reply_out(
    comment: EventComment,
    event: Event,
    viewer,
    co_host_pks: set[str] | None = None,
) -> EventCommentReplyOut:
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
        author_display_name=visible_display_name(comment.author, viewer),
        author_photo_url=_safe_photo_url(comment.author),
        body="" if is_deleted else comment.body,
        is_deleted=is_deleted,
        created_at=comment.created_at,
        reactions=reactions,
        can_delete=_can_delete_comment(event, comment, viewer, co_host_pks=co_host_pks),
    )


def _comment_out(
    comment: EventComment,
    event: Event,
    viewer,
    co_host_pks: set[str] | None = None,
) -> EventCommentOut:
    reply_list = sorted(comment.replies.all(), key=lambda r: r.created_at)
    base = _comment_reply_out(comment, event, viewer, co_host_pks=co_host_pks)
    return EventCommentOut(
        **base.model_dump(),
        replies=[_comment_reply_out(r, event, viewer, co_host_pks=co_host_pks) for r in reply_list],
    )


def _build_list_out(event: Event, viewer) -> EventCommentListOut:
    co_host_pks = {str(u.pk) for u in event.co_hosts.all()}  # uses prefetch cache
    comments = (
        EventComment.objects.filter(event=event, parent__isnull=True)
        .select_related("author")
        .prefetch_related("replies__author", "reactions", "replies__reactions")
        .order_by("-created_at")
    )
    can_post = _can_post_comments(event, viewer, co_host_pks=co_host_pks)
    if viewer is None:
        reason: str | None = "login_required"
    elif not can_post:
        reason = "rsvp_required"
    else:
        reason = None
    return EventCommentListOut(
        items=[_comment_out(c, event, viewer, co_host_pks=co_host_pks) for c in comments],
        can_post=can_post,
        cannot_post_reason=reason,
    )


def _require_rsvp_for_post(event: Event, user) -> None:
    if not _can_post_comments(event, user):
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
    viewer = resolve_event_viewer(request, event_id)
    _enforce_event_read_visibility(event, viewer)
    return Status(200, _build_list_out(event, viewer))


@router.post(
    "/events/{event_id}/comments/",
    response={201: EventCommentOut, 403: ErrorOut, 404: ErrorOut, 422: ErrorOut, 429: ErrorOut},
    auth=_optional_jwt,
)
@rate_limit(key_func=client_ip, rate="10/m")
def post_comment(request, event_id: UUID, payload: CommentBodyIn):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    user = resolve_event_viewer(request, event_id)
    _enforce_event_read_visibility(event, user)
    _require_rsvp_for_post(event, user)
    with transaction.atomic():
        comment = EventComment.objects.create(event=event, author=user, body=payload.body)
        notify_event_comment(comment)
    broadcast_event_update(event, exclude_user_ids={str(user.pk)})
    return Status(201, _comment_out(comment, event, user))


@router.post(
    "/events/{event_id}/comments/{comment_id}/replies/",
    response={
        201: EventCommentReplyOut,
        403: ErrorOut,
        404: ErrorOut,
        422: ErrorOut,
        429: ErrorOut,
    },
    auth=_optional_jwt,
)
@rate_limit(key_func=client_ip, rate="10/m")
def post_reply(request, event_id: UUID, comment_id: UUID, payload: CommentBodyIn):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    user = resolve_event_viewer(request, event_id)
    _enforce_event_read_visibility(event, user)
    _require_rsvp_for_post(event, user)
    try:
        parent = EventComment.objects.get(id=comment_id, event=event)
    except EventComment.DoesNotExist:
        raise_validation(Code.Comment.NOT_FOUND, status_code=404)
    if parent.deleted_at is not None:
        raise_validation(Code.Comment.NOT_FOUND, status_code=404)
    if parent.parent_id is not None:
        raise_validation(Code.Comment.REPLY_DEPTH_EXCEEDED, status_code=422)
    with transaction.atomic():
        reply = EventComment.objects.create(
            event=event, author=user, body=payload.body, parent=parent
        )
        notify_comment_reply(reply)
    broadcast_event_update(event, exclude_user_ids={str(user.pk)})
    return Status(201, _comment_reply_out(reply, event, user))


@router.delete(
    "/events/{event_id}/comments/{comment_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=_optional_jwt,
)
@rate_limit(key_func=client_ip, rate="10/m")
def delete_comment(request, event_id: UUID, comment_id: UUID):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    user = resolve_event_viewer(request, event_id)
    _enforce_event_read_visibility(event, user)
    try:
        comment = EventComment.objects.get(id=comment_id, event=event)
    except EventComment.DoesNotExist:
        raise_validation(Code.Comment.NOT_FOUND, status_code=404)
    if not _can_delete_comment(event, comment, user):
        raise_validation(Code.Comment.PERM_DENIED, status_code=403, action="delete_comment")
    if comment.deleted_at is None:
        with transaction.atomic():
            comment.deleted_at = timezone.now()
            comment.save(update_fields=["deleted_at", "updated_at"])
        broadcast_event_update(event, exclude_user_ids={str(user.pk)})
    return Status(204, None)


_VALID_EMOJIS = {e.value for e in ReactionEmoji}


@router.post(
    "/events/{event_id}/comments/{comment_id}/reactions/",
    response={
        200: EventCommentOut,
        403: ErrorOut,
        404: ErrorOut,
        422: ErrorOut,
        429: ErrorOut,
    },
    auth=_optional_jwt,
)
@rate_limit(key_func=client_ip, rate="10/m")
def toggle_reaction(request, event_id: UUID, comment_id: UUID, payload: ReactionToggleIn):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    user = resolve_event_viewer(request, event_id)
    _enforce_event_read_visibility(event, user)
    _require_rsvp_for_post(event, user)
    if payload.emoji not in _VALID_EMOJIS:
        raise_validation(Code.Comment.INVALID_EMOJI, status_code=422)
    try:
        comment = EventComment.objects.get(id=comment_id, event=event)
    except EventComment.DoesNotExist:
        raise_validation(Code.Comment.NOT_FOUND, status_code=404)
    if comment.deleted_at is not None:
        raise_validation(Code.Comment.NOT_FOUND, status_code=404)
    with transaction.atomic():
        existing = EventCommentReaction.objects.filter(
            comment=comment, user=user, emoji=payload.emoji
        ).first()
        if existing:
            existing.delete()
        else:
            EventCommentReaction.objects.create(comment=comment, user=user, emoji=payload.emoji)
    # The toggle endpoint returns the parent top-level comment so the FE can
    # update either a top-level row (when comment is top-level) or the reply's
    # row (when comment is a reply). When it's a reply, we return the parent.
    target_id = comment.id if comment.parent_id is None else comment.parent_id
    target = (
        EventComment.objects.select_related("author")
        .prefetch_related("replies__author", "reactions", "replies__reactions")
        .get(id=target_id)
    )
    return Status(200, _comment_out(target, event, user))
