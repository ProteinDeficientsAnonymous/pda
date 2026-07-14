"""Seed the staging deploy with events, single-permission roles, and matching users."""

import os
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from users.models import NonMemberRsvpToken, User
from users.permissions import PermissionKey
from users.roles import Role

from community.models import Event, EventRSVP, EventType, RSVPStatus

from ._seed_staging_data import (
    MEMBER_RSVP_SPECS,
    NON_MEMBER_EVENT_TITLE,
    NON_MEMBER_SPECS,
    PASSWORD,
    STAGING_EVENTS,
    TOKEN_EXPIRED,
    TOKEN_NONE,
    cond_email,
    cond_phone,
    condition_combinations,
    condition_label,
    is_seed_allowed,
    nonmember_email,
    nonmember_phone,
    perm_email,
    perm_phone,
)


class Command(BaseCommand):
    help = "Seed staging with events, single-permission roles, and matching users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true", help="Delete staging-scoped rows first."
        )
        parser.add_argument(
            "--force", action="store_true", help="Run even if the environment is not staging."
        )

    def handle(self, *args, **options):
        env_name = os.environ.get("RAILWAY_ENVIRONMENT_NAME")
        self.stdout.write(f"detected environment: {env_name or 'local/unset'}")
        if not is_seed_allowed(env_name, force=options["force"]):
            raise CommandError(
                f"refusing to seed in environment '{env_name}'. pass --force to override."
            )

        with transaction.atomic():
            if options["reset"]:
                self._reset()
            roles = self._seed_perm_roles()
            perm_users = self._seed_perm_users(roles)
            cond_users = self._seed_condition_users()
            admin = perm_users[0] if perm_users else None
            events = self._seed_events(admin)
            self._seed_member_rsvps(cond_users, events)
            non_members = self._seed_non_members(events)
        self._print_summary(
            {
                "roles": roles,
                "perm_users": perm_users,
                "cond_users": cond_users,
                "events": events,
                "non_members": non_members,
            }
        )

    def _reset(self) -> None:
        Event.objects.filter(title__startswith="[staging] ").delete()
        Event.objects.filter(title=NON_MEMBER_EVENT_TITLE).delete()
        User.objects.filter(phone_number__startswith="+170255501").delete()
        User.objects.filter(phone_number__startswith="+170255502").delete()
        User.objects.filter(phone_number__startswith="+170255503").delete()
        Role.objects.filter(name__startswith="perm: ").delete()
        self.stdout.write("  reset: removed staging-scoped rows")

    def _seed_perm_roles(self) -> dict[str, Role]:
        roles: dict[str, Role] = {}
        for key in PermissionKey.values:
            role, created = Role.objects.get_or_create(
                name=f"perm: {key}",
                defaults={"permissions": [key], "is_default": False},
            )
            if not created and (role.permissions != [key] or role.is_default):
                role.permissions = [key]
                role.is_default = False
                role.save(update_fields=["permissions", "is_default"])
            roles[key] = role
            self.stdout.write(f"  {'created' if created else 'exists'} role: {role.name}")
        return roles

    def _seed_perm_users(self, roles: dict[str, Role]) -> list[User]:
        users: list[User] = []
        now = timezone.now()
        for index, key in enumerate(PermissionKey.values):
            user, created = User.objects.get_or_create(
                phone_number=perm_phone(index),
                defaults={
                    "first_name": f"perm: {key}",
                    "email": perm_email(key),
                    "is_member": True,
                    "needs_onboarding": False,
                    "onboarded_at": now,
                    "guidelines_consent_at": now,
                    "sms_consent_at": now,
                },
            )
            if created:
                user.set_password(PASSWORD)
                user.save(update_fields=["password"])
            user.roles.set([roles[key]])
            users.append(user)
            self.stdout.write(f"  {'created' if created else 'exists'} user: {user.full_name}")
        return users

    def _member_role(self) -> Role:
        role, _ = Role.objects.get_or_create(name="member", defaults={"is_default": True})
        return role

    def _apply_condition_user_fields(self, user, combo, index, now) -> None:
        has_email, guidelines_done, sms_done = combo
        user.email = cond_email(index) if has_email else None
        user.guidelines_consent_at = now if guidelines_done else None
        user.sms_consent_at = now if sms_done else None
        user.needs_onboarding = False
        user.onboarded_at = now
        user.first_name = condition_label(combo)
        user.last_name = ""
        user.save(
            update_fields=[
                "email",
                "guidelines_consent_at",
                "sms_consent_at",
                "needs_onboarding",
                "onboarded_at",
                "first_name",
                "last_name",
            ]
        )

    def _seed_condition_users(self) -> list[User]:
        member_role = self._member_role()
        now = timezone.now()
        users: list[User] = []
        for index, combo in enumerate(condition_combinations()):
            user, created = User.objects.get_or_create(
                phone_number=cond_phone(index),
                defaults={"first_name": condition_label(combo), "is_member": True},
            )
            self._apply_condition_user_fields(user, combo, index, now)
            if created:
                user.set_password(PASSWORD)
                user.save(update_fields=["password"])
            user.roles.set([member_role])
            users.append(user)
            self.stdout.write(f"  {'created' if created else 'exists'} user: {user.full_name}")
        return users

    def _seed_events(self, created_by) -> list[Event]:
        now = timezone.now()
        events: list[Event] = []
        for data in STAGING_EVENTS:
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
                    "max_attendees": data.max_attendees,
                    "created_by": created_by,
                },
            )
            events.append(event)
            self.stdout.write(f"  {'created' if created else 'exists'} event: {data.title}")
        return events

    def _apply_rsvps(self, user, rsvps, events_by_title: dict) -> None:
        for rsvp in rsvps:
            event = events_by_title.get(rsvp.event_title)
            if event is not None:
                EventRSVP.objects.update_or_create(
                    event=event,
                    user=user,
                    defaults={"status": rsvp.status, "attendance": rsvp.attendance},
                )

    def _seed_member_rsvps(self, cond_users: list[User], events: list[Event]) -> None:
        events_by_title = {e.title: e for e in events}
        for spec in MEMBER_RSVP_SPECS:
            if spec.cond_index >= len(cond_users):
                continue
            self._apply_rsvps(cond_users[spec.cond_index], spec.rsvps, events_by_title)
        self.stdout.write(f"  seeded member rsvps for {len(MEMBER_RSVP_SPECS)} members")

    def _ensure_non_member(self, index: int, spec) -> User:
        user, created = User.objects.get_or_create(
            phone_number=nonmember_phone(index),
            defaults={
                "first_name": spec.label,
                "email": nonmember_email(index) if spec.has_email else None,
                "is_member": False,
            },
        )
        user.email = nonmember_email(index) if spec.has_email else None
        user.save(update_fields=["email"])
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        self.stdout.write(f"  {'created' if created else 'exists'} non-member: {spec.label}")
        return user

    def _apply_token_state(self, user, token_state: str) -> None:
        if token_state == TOKEN_NONE:
            return
        if token_state == TOKEN_EXPIRED:
            existing = user.rsvp_tokens.first()
            if existing is not None and existing.is_expired:
                return
            user.rsvp_tokens.all().delete()
            NonMemberRsvpToken.objects.create(
                user=user,
                token=secrets.token_urlsafe(32),
                expires_at=timezone.now() - timedelta(days=1),
            )
            return
        NonMemberRsvpToken.issue_or_extend(user)

    def _seed_non_members(self, events: list[Event]) -> list[User]:
        events_by_title = {e.title: e for e in events}
        users: list[User] = []
        for index, spec in enumerate(NON_MEMBER_SPECS):
            user = self._ensure_non_member(index, spec)
            self._apply_rsvps(user, spec.rsvps, events_by_title)
            self._apply_token_state(user, spec.token_state)
            users.append(user)
        return users

    def _print_summary(self, result: dict) -> None:
        self.stdout.write("")
        self.stdout.write(f"password for all seeded users: {PASSWORD}")
        self.stdout.write(
            f"events: {len(result['events'])}  roles: {len(result['roles'])}  "
            f"perm users: {len(result['perm_users'])}  "
            f"condition users: {len(result['cond_users'])}  "
            f"non-member users: {len(result['non_members'])}"
        )
        self._print_official_events(result["events"])
        self.stdout.write("non-member users (phone -> manage link):")
        for user in result["non_members"]:
            token = NonMemberRsvpToken.objects.filter(user=user).order_by("-created_at").first()
            if token is None or not token.is_valid:
                state = "expired token" if token is not None else "no token"
                self.stdout.write(f"  {user.phone_number} -> ({state})")
                continue
            url = f"{settings.FRONTEND_BASE_URL}/my-rsvps?token={token.token}"
            self.stdout.write(f"  {user.phone_number} -> {url}")

    def _print_official_events(self, events: list[Event]) -> None:
        official = [e for e in events if e.event_type == EventType.OFFICIAL and e.rsvp_enabled]
        self.stdout.write("official rsvp events (title -> attending/waitlisted, cap):")
        for event in official:
            rsvps = list(event.rsvps.all())
            attending = sum(1 for r in rsvps if r.status == RSVPStatus.ATTENDING)
            waitlisted = sum(1 for r in rsvps if r.status == RSVPStatus.WAITLISTED)
            cap = event.max_attendees if event.max_attendees is not None else "∞"
            self.stdout.write(f"  '{event.title}' -> {attending}/{waitlisted}, cap {cap}")
