from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0073_whatsapplinkconfig"),
    ]

    operations = [
        migrations.CreateModel(
            name="MemberPromotionMessageTemplate",
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
                ("body", models.TextField(default="", max_length=4000)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Member Promotion Message Template",
                "verbose_name_plural": "Member Promotion Message Template",
            },
        ),
    ]
