from django.db import migrations, models


def opt_in_existing(apps, schema_editor):
    # 0046 added the column off. Existing rows have not chosen yet.
    User = apps.get_model("users", "User")
    User.objects.filter(veganniversary_shoutout_opt_in=False).update(
        veganniversary_shoutout_opt_in=True
    )


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0046_user_veganniversary"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="veganniversary_shoutout_opt_in",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(opt_in_existing, migrations.RunPython.noop),
    ]
