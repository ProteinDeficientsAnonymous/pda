import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

STATUS_CHOICES = [
    ("none", "none"),
    ("tentative", "tentative"),
    ("active_member", "active member"),
    ("attendance_paused", "attendance paused"),
    ("archived", "archived"),
    ("guidelines_paused", "guidelines paused"),
]


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0057_merge_20261108_1838"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="membership_status",
            field=models.CharField(
                choices=STATUS_CHOICES, db_index=True, default="none", max_length=20
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="membership_status_changed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="membership_status_changed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="status_before_archive",
            field=models.CharField(blank=True, choices=STATUS_CHOICES, max_length=20, null=True),
        ),
    ]
