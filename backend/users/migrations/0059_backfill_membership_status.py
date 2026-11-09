from django.db import migrations
from django.db.models import Exists, OuterRef


def backfill_membership_status(apps, schema_editor):
    User = apps.get_model("users", "User")
    JoinRequest = apps.get_model("community", "JoinRequest")

    def has_request(**filters):
        return Exists(JoinRequest.objects.filter(user=OuterRef("pk"), **filters))

    # Lowest precedence first; each later update overwrites the earlier ones.
    User.objects.update(membership_status="public_rsvper")
    User.objects.filter(has_request(status="rejected", tentative_at__isnull=False)).update(
        membership_status="rejected"
    )
    User.objects.filter(has_request(status="tentative")).update(membership_status="tentative")
    User.objects.filter(is_member=True).update(membership_status="member")
    User.objects.filter(attendance_paused_at__isnull=False).update(
        membership_status="attendance_paused"
    )
    User.objects.filter(archived_at__isnull=False).update(membership_status="archived")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0058_user_membership_status"),
        ("community", "0132_member_restored_email_template"),
    ]

    operations = [
        migrations.RunPython(backfill_membership_status, migrations.RunPython.noop),
    ]
