"""Seed the staging deploy with events, single-permission roles, and matching users."""

import os
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from community.models import Event

from ._seed_staging_data import (
    PASSWORD,
    STAGING_EVENTS,
    cond_email,
    cond_phone,
    condition_combinations,
    condition_label,
    is_seed_allowed,
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
        self._print_summary(roles, perm_users, cond_users, events)

    def _reset(self) -> None:
        Event.objects.filter(title__startswith="[staging] ").delete()
        User.objects.filter(phone_number__startswith="+170255501").delete()
        User.objects.filter(phone_number__startswith="+170255502").delete()
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
                    "display_name": f"perm: {key}",
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
            self.stdout.write(f"  {'created' if created else 'exists'} user: {user.display_name}")
        return users

    def _member_role(self) -> Role:
        role, _ = Role.objects.get_or_create(name="member", defaults={"is_default": True})
        return role

    def _seed_condition_users(self) -> list[User]:
        member_role = self._member_role()
        now = timezone.now()
        users: list[User] = []
        for index, combo in enumerate(condition_combinations()):
            has_email, guidelines_done, sms_done = combo
            user, created = User.objects.get_or_create(
                phone_number=cond_phone(index),
                defaults={"display_name": condition_label(combo), "is_member": True},
            )
            user.email = cond_email(index) if has_email else None
            user.guidelines_consent_at = now if guidelines_done else None
            user.sms_consent_at = now if sms_done else None
            user.needs_onboarding = False
            user.onboarded_at = now
            user.display_name = condition_label(combo)
            user.save(
                update_fields=[
                    "email",
                    "guidelines_consent_at",
                    "sms_consent_at",
                    "needs_onboarding",
                    "onboarded_at",
                    "display_name",
                ]
            )
            if created:
                user.set_password(PASSWORD)
                user.save(update_fields=["password"])
            user.roles.set([member_role])
            users.append(user)
            self.stdout.write(f"  {'created' if created else 'exists'} user: {user.display_name}")
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
                    "created_by": created_by,
                },
            )
            events.append(event)
            self.stdout.write(f"  {'created' if created else 'exists'} event: {data.title}")
        return events

    def _print_summary(self, roles, perm_users, cond_users, events) -> None:
        self.stdout.write("")
        self.stdout.write(f"password for all seeded users: {PASSWORD}")
        self.stdout.write(
            f"events: {len(events)}  roles: {len(roles)}  "
            f"perm users: {len(perm_users)}  condition users: {len(cond_users)}"
        )
        self.stdout.write("per-permission users (phone -> role):")
        for user in perm_users:
            names = ", ".join(user.roles.values_list("name", flat=True))
            self.stdout.write(f"  {user.phone_number} -> {names}")
        self.stdout.write("profile-condition users (phone -> pattern):")
        for user in cond_users:
            self.stdout.write(f"  {user.phone_number} -> {user.display_name}")
