from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0133_joinrequest_status_changed"),
        # users.0059 reads tentative_at, so it must run before the column goes.
        ("users", "0065_remove_user_is_member"),
    ]

    operations = [
        migrations.RemoveField(model_name="joinrequest", name="tentative_at"),
        migrations.RemoveField(model_name="joinrequest", name="tentative_by"),
        migrations.RemoveField(model_name="joinrequest", name="approved_at"),
        migrations.RemoveField(model_name="joinrequest", name="approved_by"),
        migrations.RemoveField(model_name="joinrequest", name="rejected_at"),
        migrations.RemoveField(model_name="joinrequest", name="rejected_by"),
    ]
