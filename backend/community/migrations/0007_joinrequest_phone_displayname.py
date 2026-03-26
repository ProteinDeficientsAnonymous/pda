from django.db import migrations, models


def backfill_phone_numbers(apps, schema_editor):
    JoinRequest = apps.get_model("community", "JoinRequest")
    for i, jr in enumerate(
        JoinRequest.objects.filter(phone_number="").order_by("submitted_at"), start=1
    ):
        jr.phone_number = f"+1000000000{i}"
        jr.save(update_fields=["phone_number"])


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0006_eventrsvp"),
    ]

    operations = [
        migrations.RenameField(
            model_name="joinrequest",
            old_name="name",
            new_name="display_name",
        ),
        migrations.AlterField(
            model_name="joinrequest",
            name="display_name",
            field=models.CharField(max_length=64),
        ),
        migrations.AddField(
            model_name="joinrequest",
            name="phone_number",
            field=models.CharField(default="", max_length=20),
        ),
        migrations.RunPython(backfill_phone_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="joinrequest",
            name="email",
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
