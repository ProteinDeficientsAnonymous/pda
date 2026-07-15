from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0072_seed_tentative_approval_message"),
    ]

    operations = [
        migrations.CreateModel(
            name="WhatsAppLinkConfig",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("link", models.CharField(default="", max_length=200)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "WhatsApp Link",
                "verbose_name_plural": "WhatsApp Link",
            },
        ),
    ]
