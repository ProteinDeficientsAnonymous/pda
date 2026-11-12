"""An admin plus one person per membership status for `seed_staging`."""

from dataclasses import dataclass

from django.utils import timezone
from users.models import MembershipStatus, User
from users.roles import Role

from community.join_requests.approval import provision_tentative_user
from community.models import JoinRequest, JoinRequestStatus

from ._seed_shared import get_or_create_seed_user
from ._seed_staging_data import PASSWORD

STATUS_PHONE_PREFIX = "+170255507"
ADMIN_ROLES = ("admin", "member")


def status_phone(index: int) -> str:
    return f"{STATUS_PHONE_PREFIX}{index:02d}"


@dataclass(frozen=True)
class StatusSpec:
    first_name: str
    status: MembershipStatus
    archived_from: MembershipStatus | None = None

    @property
    def label(self) -> str:
        return f"{self.status} (from {self.archived_from})" if self.archived_from else self.status


# Index 0 is the admin; each spec's phone is status_phone(position + 1).
STATUS_SPECS = [
    StatusSpec("Tentative", MembershipStatus.TENTATIVE),
    StatusSpec("Attendance-Paused", MembershipStatus.ATTENDANCE_PAUSED),
    StatusSpec("Guidelines-Paused", MembershipStatus.GUIDELINES_PAUSED),
    StatusSpec("Archived", MembershipStatus.ARCHIVED, MembershipStatus.ACTIVE_MEMBER),
    StatusSpec("Archived-Paused", MembershipStatus.ARCHIVED, MembershipStatus.ATTENDANCE_PAUSED),
]


def reset_status_join_requests() -> None:
    JoinRequest.objects.filter(phone_number__startswith=STATUS_PHONE_PREFIX).delete()


def _person_fields(first_name: str, index: int) -> dict:
    now = timezone.now()
    return {
        "first_name": first_name,
        "last_name": "Staging",
        "email": f"status{index:02d}@staging.example",
        "guidelines_consent_at": now,
        "sms_consent_at": now,
    }


def _onboarded_defaults(first_name: str, index: int) -> dict:
    return {
        **_person_fields(first_name, index),
        "membership_status": MembershipStatus.ACTIVE_MEMBER,
        "needs_onboarding": False,
        "onboarded_at": timezone.now(),
    }


def _seed_admin(stdout) -> User:
    roles = [
        Role.objects.get_or_create(name=n, defaults={"is_default": True})[0] for n in ADMIN_ROLES
    ]
    user, created = get_or_create_seed_user(
        status_phone(0), PASSWORD, _onboarded_defaults("Admin", 0), roles
    )
    user.roles.add(*roles)
    stdout.write(f"  {'created' if created else 'exists'} admin: {user.full_name}")
    return user


def _seed_tentative(spec: StatusSpec, index: int, admin: User) -> tuple[User, bool]:
    now = timezone.now()
    join_request, created = JoinRequest.objects.get_or_create(
        phone_number=status_phone(index),
        defaults={
            **_person_fields(spec.first_name, index),
            "status": JoinRequestStatus.TENTATIVE,
            "status_changed_at": now,
            "status_changed_by": admin,
        },
    )
    if not created and join_request.user is not None:
        return join_request.user, False
    user, _ = provision_tentative_user(join_request, admin)
    # Skip the magic link's /new-password step so testers sign in with the seed password.
    user.set_password(PASSWORD)
    user.needs_onboarding = False
    user.onboarded_at = now
    user.save(update_fields=["password", "needs_onboarding", "onboarded_at"])
    return user, True


def _apply_status(user: User, spec: StatusSpec, admin: User) -> None:
    # Mirrors apply_attendance_pause / archive_user, which sit in private users modules.
    pause = spec.archived_from or spec.status
    fields: list[str] = []
    if pause == MembershipStatus.GUIDELINES_PAUSED:
        fields = user.apply_guidelines_pause(by=admin)
    elif pause == MembershipStatus.ATTENDANCE_PAUSED:
        user.attendance_paused_at = timezone.now()
        fields = ["attendance_paused_at", *user.set_membership_status(pause, by=admin)]
    if spec.archived_from is not None:
        user.archived_at = timezone.now()
        user.status_before_archive = user.membership_status
        fields += ["archived_at", "status_before_archive"]
        fields += user.set_membership_status(MembershipStatus.ARCHIVED, by=admin)
    user.save(update_fields=fields)


def _seed_member_in_status(spec: StatusSpec, index: int, admin: User) -> tuple[User, bool]:
    defaults = _onboarded_defaults(spec.first_name, index)
    roles = [Role.objects.get(name="member")]
    user, created = get_or_create_seed_user(status_phone(index), PASSWORD, defaults, roles)
    if created:
        _apply_status(user, spec, admin)
    return user, created


def seed_status_people(stdout) -> list[tuple[str, User]]:
    """Seed an admin, then one person per non-default membership status; returns (label, user)."""
    admin = _seed_admin(stdout)
    people: list[tuple[str, User]] = [("admin", admin)]
    for position, spec in enumerate(STATUS_SPECS):
        index = position + 1
        if spec.status == MembershipStatus.TENTATIVE:
            user, created = _seed_tentative(spec, index, admin)
        else:
            user, created = _seed_member_in_status(spec, index, admin)
        people.append((spec.label, user))
        stdout.write(f"  {'created' if created else 'exists'} {spec.label} user: {user.full_name}")
    return people
