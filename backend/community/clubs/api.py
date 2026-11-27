"""Club list endpoints: public read, `manage_events` to create, edit and delete."""

import logging
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from django.db import IntegrityError, transaction
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field
from users.helpers import visible_name
from users.models import User
from users.permissions import PermissionKey

from community.models import Club
from community.models.club import CLUB_NAME_MAX, CLUB_REQUIREMENTS_MAX
from community.shared import ErrorOut
from community.validation import Code, raise_validation

router = Router()


class ClubOut(BaseModel):
    id: str
    name: str
    requirements: str


class ClubIn(BaseModel):
    name: str = Field(max_length=CLUB_NAME_MAX)
    requirements: str = Field(default="", max_length=CLUB_REQUIREMENTS_MAX)


class ClubRepOut(BaseModel):
    id: str
    full_name: str
    phone_number: str


class ClubRepsOut(BaseModel):
    club_id: str
    reps: list[ClubRepOut]


class ClubRepsIn(BaseModel):
    user_ids: list[UUID]


def club_out(club: Club) -> ClubOut:
    return ClubOut(id=str(club.id), name=club.name, requirements=club.requirements)


def _require_manage_clubs(request, endpoint: str, target_id: str = "") -> None:
    if request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        return
    audit_log(
        logging.WARNING,
        "permission_denied",
        request,
        persist=False,
        target=AuditTarget(
            type=AuditTargetType.CLUB,
            id=target_id,
            details={"endpoint": endpoint, "required_permission": PermissionKey.MANAGE_EVENTS},
        ),
    )
    raise_validation(Code.Perm.DENIED, status_code=403, action="manage_events")


def _get_club(club_id: UUID) -> Club:
    club = Club.objects.filter(id=club_id).first()
    if club is None:
        raise_validation(Code.Club.NOT_FOUND, status_code=404)
    return club


def _save_club(club: Club, payload: ClubIn) -> None:
    """Apply the payload and save; raises on a blank or duplicate name."""
    name = payload.name.strip()
    if not name:
        raise_validation(Code.Club.NAME_REQUIRED, field="name")
    duplicate = Club.objects.filter(name__iexact=name).exclude(pk=club.pk).exists()
    if duplicate:
        raise_validation(Code.Club.NAME_ALREADY_EXISTS, field="name")
    club.name = name
    club.requirements = payload.requirements.strip()
    try:
        with transaction.atomic():
            club.save()
    except IntegrityError:
        raise_validation(Code.Club.NAME_ALREADY_EXISTS, field="name")


def _audit(request, action: str, club: Club, level: int = logging.INFO) -> None:
    audit_log(
        level,
        action,
        request,
        target=AuditTarget(type=AuditTargetType.CLUB, id=str(club.id), details={"name": club.name}),
    )


@router.get("/clubs/", response={200: list[ClubOut]}, auth=None)
def list_clubs(request):
    return Status(200, [club_out(c) for c in Club.objects.all()])


@router.post("/clubs/", response={201: ClubOut, 400: ErrorOut, 403: ErrorOut}, auth=gated_jwt)
def create_club(request, payload: ClubIn):
    _require_manage_clubs(request, "create_club")
    club = Club()
    _save_club(club, payload)
    _audit(request, "club_created", club)
    return Status(201, club_out(club))


def _reps_out(club: Club, viewer: User) -> ClubRepsOut:
    reps = [
        ClubRepOut(
            id=str(u.id),
            full_name=visible_name(u, viewer)[1],
            phone_number=u.phone_number if u.show_phone else "",
        )
        for u in club.reps.all()
    ]
    return ClubRepsOut(club_id=str(club.id), reps=sorted(reps, key=lambda r: (r.full_name, r.id)))


@router.get("/clubs/reps/", response={200: list[ClubRepsOut], 403: ErrorOut}, auth=gated_jwt)
def list_club_reps(request):
    _require_manage_clubs(request, "list_club_reps")
    clubs = Club.objects.prefetch_related("reps")
    return Status(200, [_reps_out(c, request.auth) for c in clubs])


@router.put(
    "/clubs/{club_id}/reps/",
    response={200: ClubRepsOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def set_club_reps(request, club_id: UUID, payload: ClubRepsIn):
    _require_manage_clubs(request, "set_club_reps", target_id=str(club_id))
    club = _get_club(club_id)
    ids = set(payload.user_ids)
    kept = list(club.reps.filter(id__in=ids))
    added_ids = ids - {u.id for u in kept}
    added = list(User.objects.members().filter(id__in=added_ids))
    if len(added) != len(added_ids):
        raise_validation(Code.Club.REP_NOT_ELIGIBLE, field="user_ids", status_code=400)
    users = kept + added
    with transaction.atomic():
        before = {str(i) for i in club.reps.values_list("id", flat=True)}
        club.reps.set(users)
    after = {str(u.id) for u in users}
    audit_log(
        logging.INFO,
        "club_reps_updated",
        request,
        target=AuditTarget(
            type=AuditTargetType.CLUB,
            id=str(club.id),
            details={
                "name": club.name,
                "added": sorted(after - before),
                "removed": sorted(before - after),
            },
        ),
    )
    return Status(200, _reps_out(club, request.auth))


@router.patch(
    "/clubs/{club_id}/",
    response={200: ClubOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def update_club(request, club_id: UUID, payload: ClubIn):
    _require_manage_clubs(request, "update_club", target_id=str(club_id))
    club = _get_club(club_id)
    _save_club(club, payload)
    _audit(request, "club_updated", club)
    return Status(200, club_out(club))


@router.delete(
    "/clubs/{club_id}/", response={204: None, 403: ErrorOut, 404: ErrorOut}, auth=gated_jwt
)
def delete_club(request, club_id: UUID):
    _require_manage_clubs(request, "delete_club", target_id=str(club_id))
    club = _get_club(club_id)
    _audit(request, "club_deleted", club, level=logging.WARNING)
    club.delete()
    return Status(204, None)
