from django.db import migrations
from django.db.models import Exists, F, OuterRef, Q

ARCHIVED = Q(archived_at__isnull=False)


def backfill_membership_status(apps, schema_editor):
    User = apps.get_model("users", "User")
    JoinRequest = apps.get_model("community", "JoinRequest")
    tentative = JoinRequest.objects.filter(user=OuterRef("pk"), status="tentative")

    # Lowest precedence first; each later update overwrites the earlier ones.
    User.objects.update(membership_status="none")
    User.objects.filter(Exists(tentative)).update(membership_status="tentative")
    User.objects.filter(is_member=True).update(membership_status="active_member")
    User.objects.filter(attendance_paused_at__isnull=False).update(
        membership_status="attendance_paused"
    )
    paused = User.objects.filter(is_paused=True)
    # A guidelines pause replaces an attendance pause; is_member keeps them on the admin list.
    paused.filter(~ARCHIVED, attendance_paused_at__isnull=False).update(is_member=True)
    # Archived rows too, so a later check-in can't restore an attendance pause from under it.
    paused.update(attendance_paused_at=None)
    # Also fails closed on tentative or none rows.
    paused.filter(~ARCHIVED).update(membership_status="guidelines_paused")
    User.objects.filter(ARCHIVED).update(membership_status="archived")

    archived = User.objects.filter(ARCHIVED)
    archived.update(status_before_archive="none")
    archived.filter(is_member=True).update(status_before_archive="active_member")
    archived.filter(attendance_paused_at__isnull=False).update(
        status_before_archive="attendance_paused"
    )
    archived.filter(is_paused=True).update(status_before_archive="guidelines_paused")
    User.objects.exclude(ARCHIVED).update(status_before_archive=None)
    archived.filter(membership_status_changed_at__isnull=True).update(
        membership_status_changed_at=F("archived_at")
    )


def grant_member_role_to_attendance_paused(apps, schema_editor):
    User = apps.get_model("users", "User")
    Role = apps.get_model("users", "Role")
    member_role = Role.objects.filter(name="member", is_default=True).first()
    if member_role is None:
        return
    paused = User.objects.filter(
        Q(membership_status="attendance_paused") | Q(status_before_archive="attendance_paused")
    ).values_list("pk", flat=True)
    UserRole = User.roles.through
    UserRole.objects.bulk_create(
        [UserRole(user_id=pk, role_id=member_role.pk) for pk in paused],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0058_user_membership_status"),
        ("community", "0133_joinrequest_status_changed"),
    ]

    operations = [
        migrations.RunPython(backfill_membership_status, migrations.RunPython.noop),
        migrations.RunPython(grant_member_role_to_attendance_paused, migrations.RunPython.noop),
    ]
