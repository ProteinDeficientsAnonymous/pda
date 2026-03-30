from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0019_migrate_join_request_data"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="joinrequest",
            name="email",
        ),
        migrations.RemoveField(
            model_name="joinrequest",
            name="how_they_heard",
        ),
        migrations.RemoveField(
            model_name="joinrequest",
            name="pronouns",
        ),
        migrations.RemoveField(
            model_name="joinrequest",
            name="why_join",
        ),
    ]
