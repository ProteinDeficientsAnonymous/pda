"""Seed the staging deploy with events, single-permission roles, and matching users."""

import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from ._seed_staging_data import (
    PASSWORD,
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
            self._seed_perm_users(roles)

    def _reset(self) -> None:
        pass  # implemented in Task 3

    def _seed_perm_roles(self) -> dict[str, Role]:
        roles: dict[str, Role] = {}
        for key in PermissionKey.values:
            role, created = Role.objects.get_or_create(
                name=f"perm: {key}",
                defaults={"permissions": [key], "is_default": False},
            )
            if not created and role.permissions != [key]:
                role.permissions = [key]
                role.save(update_fields=["permissions"])
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
