from dataclasses import dataclass
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import User
from users.roles import Role

from community.models import Event, JoinRequest, JoinRequestStatus

PASSWORD = "testpass123"


@dataclass
class SeedUser:
    phone_number: str
    display_name: str
    is_superuser: bool


@dataclass
class SeedEvent:
    title: str
    description: str
    delta_days: int
    duration_hours: float
    location: str


@dataclass
class SeedJoinRequest:
    display_name: str
    phone_number: str
    why_join: str
    status: str


SEED_USERS = [
    SeedUser(
        phone_number="+17025550001",
        display_name="Seed Admin",
        is_superuser=True,
    ),
    SeedUser(
        phone_number="+17025550002",
        display_name="Seed Member",
        is_superuser=False,
    ),
]

SEED_EVENTS = [
    SeedEvent(
        title="Vegan Potluck",
        description="Bring your favourite plant-based dish to share!",
        delta_days=7,
        duration_hours=3,
        location="Community Center",
    ),
    SeedEvent(
        title="Plant-Based Cooking Workshop",
        description="Learn to make tofu scramble, cashew cheese, and more.",
        delta_days=14,
        duration_hours=2,
        location="Kitchen Lab",
    ),
    SeedEvent(
        title="Movie Night: Cowspiracy",
        description="Documentary screening followed by group discussion.",
        delta_days=21,
        duration_hours=2.5,
        location="Living Room",
    ),
]

SEED_JOIN_REQUESTS = [
    SeedJoinRequest(
        display_name="Alex Rivera",
        phone_number="+17025550010",
        why_join="I've been vegan for two years and want to connect with community.",
        status=JoinRequestStatus.PENDING,
    ),
    SeedJoinRequest(
        display_name="Jordan Chen",
        phone_number="+17025550011",
        why_join="Looking for local vegan friends and events.",
        status=JoinRequestStatus.APPROVED,
    ),
    SeedJoinRequest(
        display_name="Sam Taylor",
        phone_number="+17025550012",
        why_join="Curious about veganism.",
        status=JoinRequestStatus.REJECTED,
    ),
]


class Command(BaseCommand):
    help = "Seed the database with sample users, events, and join requests"

    def handle(self, *args, **options):
        admin_user = self._seed_users()
        self._seed_events(admin_user)
        self._seed_join_requests()
        self._print_summary()

    def _create_or_skip_user(self, data, admin_role, member_role) -> tuple[User, bool]:
        """Create user from seed data or return existing. Returns (user, created)."""
        defaults: dict[str, object] = {"display_name": data.display_name}
        if data.is_superuser:
            defaults["is_superuser"] = True
            defaults["is_staff"] = True
        user, created = User.objects.get_or_create(
            phone_number=data.phone_number, defaults=defaults
        )
        if created:
            user.set_password(PASSWORD)
            user.save()
            user.roles.add(admin_role if data.is_superuser else member_role)
            self.stdout.write(f"  Created user: {user.display_name}")
        else:
            self.stdout.write(f"  Already exists: {user.display_name}")
        return user, created

    def _seed_users(self) -> User:
        # Ensure roles exist before creating users (post_save signal needs admin role)
        admin_role, _ = Role.objects.get_or_create(name="admin", defaults={"is_default": True})
        member_role, _ = Role.objects.get_or_create(name="member", defaults={"is_default": True})

        admin_user: User | None = None
        for data in SEED_USERS:
            user, _ = self._create_or_skip_user(data, admin_role, member_role)
            if data.is_superuser:
                admin_user = user

        assert admin_user is not None, "SEED_USERS must contain a superuser entry"
        return admin_user

    def _seed_events(self, created_by: User) -> None:
        now = timezone.now()
        for data in SEED_EVENTS:
            start = now + timedelta(days=data.delta_days)
            end = start + timedelta(hours=data.duration_hours)
            _, created = Event.objects.get_or_create(
                title=data.title,
                defaults={
                    "description": data.description,
                    "start_datetime": start,
                    "end_datetime": end,
                    "location": data.location,
                    "created_by": created_by,
                },
            )
            label = "Created" if created else "Already exists"
            self.stdout.write(f"  {label} event: {data.title}")

    def _seed_join_requests(self) -> None:
        from community.models import JoinFormQuestion

        why_q = JoinFormQuestion.objects.filter(required=True).first()
        for data in SEED_JOIN_REQUESTS:
            answers = {}
            if why_q:
                answers[str(why_q.id)] = {"label": why_q.label, "answer": data.why_join}
            _, created = JoinRequest.objects.get_or_create(
                display_name=data.display_name,
                phone_number=data.phone_number,
                defaults={
                    "custom_answers": answers,
                    "status": data.status,
                },
            )
            label = "Created" if created else "Already exists"
            self.stdout.write(f"  {label} join request: {data.display_name}")

    def _print_summary(self) -> None:
        self.stdout.write("")
        self.stdout.write("Seed complete!")
        self.stdout.write(
            f"  Users: {User.objects.filter(phone_number__startswith='+1702555').count()}"
        )
        self.stdout.write(f"  Events: {Event.objects.count()}")
        self.stdout.write(f"  Join requests: {JoinRequest.objects.count()}")
        self.stdout.write("")
        self.stdout.write("Credentials (all seed users):")
        for data in SEED_USERS:
            self.stdout.write(f"  {data.display_name}: {data.phone_number} / {PASSWORD}")
