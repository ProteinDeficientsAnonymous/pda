from django.db import migrations


def carry_over_opt_outs(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(weekly_digest_opt_out=True).update(monthly_digest_opt_out=True)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0052_user_monthly_digest_sent_on"),
    ]

    operations = [
        migrations.RunPython(carry_over_opt_outs, migrations.RunPython.noop),
    ]
