from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import User
from users.roles import Role

from community.models import Event, EventRSVP, JoinRequest, JoinRequestStatus
from community.models.content import FAQ, CommunityGuidelines, HomePage
from community.models.join_form import JoinFormQuestion

from ._seed_data import (
    PASSWORD,
    SEED_EVENTS,
    SEED_FAQ,
    SEED_GUIDELINES,
    SEED_HOME_PAGE,
    SEED_JOIN_FORM_QUESTIONS,
    SEED_JOIN_REQUESTS,
    SEED_RSVPS,
    SEED_USERS,
    SeedUser,
)


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
        events = self._seed_events(admin_user)
        self._seed_rsvps(events)
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
            "is_member": True,
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

    def _seed_events(self, created_by: User) -> dict[str, Event]:
        """Seed events. Returns a title→Event mapping for RSVP seeding."""
        now = timezone.now()
        events: dict[str, Event] = {}
        for data in SEED_EVENTS:
            start = now + timedelta(days=data.delta_days)
            end = start + timedelta(hours=data.duration_hours)
            event, created = Event.objects.get_or_create(
                title=data.title,
                defaults={
                    "description": data.description,
                    "start_datetime": start,
                    "end_datetime": end,
                    "location": data.location,
                    "event_type": data.event_type,
                    "rsvp_enabled": data.rsvp_enabled,
                    "allow_plus_ones": data.allow_plus_ones,
                    "max_attendees": data.max_attendees,
                    "created_by": created_by,
                },
            )
            events[data.title] = event
            label = "Created" if created else "Already exists"
            self.stdout.write(f"  {label} event: {data.title}")
        return events

    def _seed_rsvps(self, events: dict[str, Event]) -> None:
        """Seed RSVPs so the roster, waitlist, and stats panel are QA-able.

        RSVP rows are written directly (not via the upsert endpoint) so the
        seeded statuses — including waitlisted entries and marked attendance —
        land verbatim rather than being re-derived from capacity rules.
        """
        users = {
            u.phone_number: u for u in User.objects.filter(phone_number__startswith="+1702555")
        }
        for data in SEED_RSVPS:
            event = events.get(data.event_title)
            user = users.get(data.phone_number)
            if event is None or user is None:
                self.stdout.write(
                    f"  Skipped RSVP (missing event/user): {data.event_title} / {data.phone_number}"
                )
                continue
            _, created = EventRSVP.objects.get_or_create(
                event=event,
                user=user,
                defaults={
                    "status": data.status,
                    "has_plus_one": data.has_plus_one,
                    "attendance": data.attendance,
                },
            )
            label = "Created" if created else "Already exists"
            self.stdout.write(f"  {label} RSVP: {user.display_name} → {data.event_title}")

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
        self.stdout.write(f"  RSVPs: {EventRSVP.objects.count()}")
        self.stdout.write(f"  Join requests: {JoinRequest.objects.count()}")
        self.stdout.write(f"  Join form questions: {JoinFormQuestion.objects.count()}")
        self.stdout.write("")
        self.stdout.write("Credentials (all seed users):")
        for data in SEED_USERS:
            self.stdout.write(f"  {data.display_name}: {data.phone_number} / {PASSWORD}")
