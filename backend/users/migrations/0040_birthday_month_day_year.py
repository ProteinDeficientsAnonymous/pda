from django.db import migrations, models


def backfill_birthday_parts(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.exclude(birthday=None).only("id", "birthday"):
        User.objects.filter(pk=user.pk).update(
            birthday_month=user.birthday.month,
            birthday_day=user.birthday.day,
            birthday_year=user.birthday.year,
        )


def restore_birthday_date(apps, schema_editor):
    from datetime import date

    User = apps.get_model("users", "User")
    for user in User.objects.exclude(birthday_month=None).only(
        "id", "birthday_month", "birthday_day", "birthday_year"
    ):
        User.objects.filter(pk=user.pk).update(
            birthday=date(user.birthday_year or 1904, user.birthday_month, user.birthday_day)
        )


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0039_user_show_birthday"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="birthday_day",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="birthday_month",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="birthday_year",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_birthday_parts, restore_birthday_date),
        migrations.RemoveField(
            model_name="user",
            name="birthday",
        ),
    ]
