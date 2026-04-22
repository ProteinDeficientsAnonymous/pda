from dataclasses import dataclass, field
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import User
from users.roles import Role

from community.models import Event, JoinRequest, JoinRequestStatus
from community.models.choices import EventType, JoinFormQuestionType
from community.models.content import FAQ, CommunityGuidelines, HomePage
from community.models.join_form import JoinFormQuestion

PASSWORD = "testpass123"


@dataclass
class SeedUser:
    phone_number: str
    display_name: str
    is_superuser: bool
    email: str = ""
    bio: str = ""


@dataclass
class SeedEvent:
    title: str
    description: str
    delta_days: int
    duration_hours: float
    location: str
    event_type: str = EventType.COMMUNITY


@dataclass
class SeedJoinRequest:
    display_name: str
    phone_number: str
    answers: dict[str, str]
    status: str
    decided_days_ago: int | None = None


@dataclass
class SeedJoinFormQuestion:
    label: str
    field_type: str = JoinFormQuestionType.TEXT
    required: bool = True
    options: list[str] = field(default_factory=list)
    display_order: int = 0


SEED_USERS = [
    SeedUser(
        phone_number="+17025550001",
        display_name="Seed Admin",
        is_superuser=True,
        email="admin@pda.test",
        bio="org admin — ping me if anything's broken 🌿",
    ),
    SeedUser(
        phone_number="+17025550002",
        display_name="Seed Member",
        is_superuser=False,
        email="member@pda.test",
        bio="vegan six years, big into potlucks and mutual aid.",
    ),
    SeedUser(
        phone_number="+17025550003",
        display_name="Jamie Okafor",
        is_superuser=False,
        email="jamie@pda.test",
        bio="food not bombs volunteer. cook, eat, organize.",
    ),
    SeedUser(
        phone_number="+17025550004",
        display_name="Rin Takahashi",
        is_superuser=False,
        email="rin@pda.test",
    ),
    SeedUser(
        phone_number="+17025550005",
        display_name="Ash Morales",
        is_superuser=False,
        email="ash@pda.test",
        bio="plant-based chef, always down to swap recipes.",
    ),
]

SEED_JOIN_FORM_QUESTIONS = [
    SeedJoinFormQuestion(
        label="Why do you want to join?",
        field_type=JoinFormQuestionType.TEXT,
        required=True,
        display_order=0,
    ),
    SeedJoinFormQuestion(
        label="How did you hear about us?",
        field_type=JoinFormQuestionType.TEXT,
        required=False,
        display_order=1,
    ),
    SeedJoinFormQuestion(
        label="What are your pronouns?",
        field_type=JoinFormQuestionType.TEXT,
        required=False,
        display_order=2,
    ),
]

SEED_EVENTS = [
    SeedEvent(
        title="Vegan Potluck",
        description="Bring your favourite dish to share!",
        delta_days=7,
        duration_hours=3,
        location="Community Center",
        event_type=EventType.COMMUNITY,
    ),
    SeedEvent(
        title="Plant-Based Cooking Workshop",
        description="Learn to make tofu scramble, cashew cheese, and more.",
        delta_days=14,
        duration_hours=2,
        location="Kitchen Lab",
        event_type=EventType.OFFICIAL,
    ),
    SeedEvent(
        title="Movie Night",
        description="Documentary screening followed by group discussion.",
        delta_days=21,
        duration_hours=2.5,
        location="Living Room",
        event_type=EventType.COMMUNITY,
    ),
    SeedEvent(
        title="Past Potluck (seed)",
        description="Last month's potluck — great turnout!",
        delta_days=-30,
        duration_hours=3,
        location="Community Center",
        event_type=EventType.COMMUNITY,
    ),
]

SEED_HOME_PAGE = {
    "content_html": "<p>This is seed text for the home page.</p>",
}

SEED_GUIDELINES = {
    "content_html": "<p>This is seed text for the guidelines page.</p>",
}

SEED_FAQ = {
    "content_html": "<p>This is seed text for the FAQ page.</p>",
}

SEED_JOIN_REQUESTS = [
    SeedJoinRequest(
        display_name="Alex Rivera",
        phone_number="+17025550010",
        answers={
            "Why do you want to join?": "I've been vegan for two years and want to connect with community.",
            "How did you hear about us?": "A friend told me about PDA.",
        },
        status=JoinRequestStatus.PENDING,
    ),
    SeedJoinRequest(
        display_name="Jordan Chen",
        phone_number="+17025550011",
        answers={
            "Why do you want to join?": "Looking for local vegan friends and events.",
            "What are your pronouns?": "they/them",
        },
        status=JoinRequestStatus.APPROVED,
        decided_days_ago=5,
    ),
    SeedJoinRequest(
        display_name="Sam Taylor",
        phone_number="+17025550012",
        answers={
            "Why do you want to join?": "Curious about veganism.",
        },
        status=JoinRequestStatus.REJECTED,
        decided_days_ago=3,
    ),
    SeedJoinRequest(
        display_name="Priya Raghavendra-Nakamura",
        phone_number="+17025550013",
        answers={
            "Why do you want to join?": (
                "i've been plant-based for about six months and am finally ready to find my people. "
                "looking for folks to cook with, share resources, and organize around animal liberation "
                "and broader collective liberation work."
            ),
            "How did you hear about us?": "saw a flyer at the co-op on grand ave.",
            "What are your pronouns?": "she/they",
        },
        status=JoinRequestStatus.PENDING,
    ),
    SeedJoinRequest(
        display_name="Mo",
        phone_number="+442079460958",
        answers={
            "Why do you want to join?": "moving to the area next month and want to plug in before i arrive.",
            "What are your pronouns?": "he/him",
        },
        status=JoinRequestStatus.PENDING,
    ),
    SeedJoinRequest(
        display_name="Riley Okonkwo-Vasquez",
        phone_number="+17025550015",
        answers={
            "Why do you want to join?": "food not bombs volunteer, interested in mutual aid + vegan outreach.",
            "How did you hear about us?": "instagram — pda showed up in a story reshare.",
        },
        status=JoinRequestStatus.PENDING,
    ),
    SeedJoinRequest(
        display_name="Taylor Kim",
        phone_number="+17025550016",
        answers={
            "Why do you want to join?": "just curious — not vegan yet but open to learning.",
        },
        status=JoinRequestStatus.PENDING,
    ),
    SeedJoinRequest(
        display_name="Devon Alvarez",
        phone_number="+17025550017",
        answers={
            "Why do you want to join?": "longtime abolitionist looking for aligned community.",
            "How did you hear about us?": "word of mouth at a local protest.",
            "What are your pronouns?": "they/them",
        },
        status=JoinRequestStatus.APPROVED,
        decided_days_ago=1,
    ),
]


def _seed_singleton(model_cls, seed_data: dict, fields: tuple[str, ...], cmd: "Command") -> None:
    """Populate a singleton content model only when the target fields are still empty."""
    obj = model_cls.get()
    if all(getattr(obj, f) for f in fields):
        cmd.stdout.write(f"  Already populated: {model_cls.__name__}")
        return
    for key, value in seed_data.items():
        setattr(obj, key, value)
    obj.save(update_fields=list(seed_data.keys()))
    cmd.stdout.write(f"  Seeded: {model_cls.__name__}")


class Command(BaseCommand):
    help = "Seed the database with sample users, events, and join requests"

    def handle(self, *args, **options):
        admin_user = self._seed_users()
        questions = self._seed_join_form_questions()
        self._seed_events(admin_user)
        self._seed_join_requests(questions, admin_user)
        self._seed_content()
        self._print_summary()

    def _backfill_user(self, user: User, data: "SeedUser") -> None:
        """Fill in email/bio on existing users so reseeding picks up changes."""
        updates: dict[str, str] = {}
        if data.email and not user.email:
            updates["email"] = data.email
        if data.bio and not user.bio:
            updates["bio"] = data.bio
        if not updates:
            self.stdout.write(f"  Already exists: {user.display_name}")
            return
        for k, v in updates.items():
            setattr(user, k, v)
        user.save(update_fields=list(updates.keys()))
        self.stdout.write(f"  Backfilled {', '.join(updates)}: {user.display_name}")

    def _create_or_skip_user(self, data, admin_role, member_role) -> tuple[User, bool]:
        """Create user from seed data or return existing. Returns (user, created)."""
        defaults: dict[str, object] = {
            "display_name": data.display_name,
            "email": data.email,
            "bio": data.bio,
        }
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
            self._backfill_user(user, data)
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

    def _seed_join_form_questions(self) -> dict[str, JoinFormQuestion]:
        """Seed default join form questions. Returns a label→question mapping."""
        questions: dict[str, JoinFormQuestion] = {}
        for data in SEED_JOIN_FORM_QUESTIONS:
            q, created = JoinFormQuestion.objects.get_or_create(
                label=data.label,
                defaults={
                    "field_type": data.field_type,
                    "required": data.required,
                    "options": data.options,
                    "display_order": data.display_order,
                },
            )
            label = "Created" if created else "Already exists"
            self.stdout.write(f"  {label} question: {q.label}")
            questions[q.label] = q
        return questions

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
                    "event_type": data.event_type,
                    "created_by": created_by,
                },
            )
            label = "Created" if created else "Already exists"
            self.stdout.write(f"  {label} event: {data.title}")

    def _seed_join_requests(self, questions: dict[str, JoinFormQuestion], admin_user: User) -> None:
        now = timezone.now()
        for data in SEED_JOIN_REQUESTS:
            custom_answers = {
                str(questions[label].id): {"label": label, "answer": answer}
                for label, answer in data.answers.items()
                if label in questions
            }
            defaults: dict[str, object] = {
                "custom_answers": custom_answers,
                "status": data.status,
            }
            if data.decided_days_ago is not None:
                decided_at = now - timedelta(days=data.decided_days_ago)
                if data.status == JoinRequestStatus.APPROVED:
                    defaults["approved_at"] = decided_at
                    defaults["approved_by"] = admin_user
                elif data.status == JoinRequestStatus.REJECTED:
                    defaults["rejected_at"] = decided_at
                    defaults["rejected_by"] = admin_user
            _, created = JoinRequest.objects.get_or_create(
                display_name=data.display_name,
                phone_number=data.phone_number,
                defaults=defaults,
            )
            label = "Created" if created else "Already exists"
            self.stdout.write(f"  {label} join request: {data.display_name}")

    def _seed_content(self) -> None:
        _seed_singleton(HomePage, SEED_HOME_PAGE, ("content_html",), self)
        _seed_singleton(CommunityGuidelines, SEED_GUIDELINES, ("content_html",), self)
        _seed_singleton(FAQ, SEED_FAQ, ("content_html",), self)

    def _print_summary(self) -> None:
        self.stdout.write("")
        self.stdout.write("Seed complete!")
        self.stdout.write(
            f"  Users: {User.objects.filter(phone_number__startswith='+1702555').count()}"
        )
        self.stdout.write(f"  Events: {Event.objects.count()}")
        self.stdout.write(f"  Join requests: {JoinRequest.objects.count()}")
        self.stdout.write(f"  Join form questions: {JoinFormQuestion.objects.count()}")
        self.stdout.write("")
        self.stdout.write("Credentials (all seed users):")
        for data in SEED_USERS:
            self.stdout.write(f"  {data.display_name}: {data.phone_number} / {PASSWORD}")
