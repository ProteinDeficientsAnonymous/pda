from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0070_alter_joinrequest_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="TentativeApprovalMessageTemplate",
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
                "verbose_name": "Tentative Approval Message Template",
                "verbose_name_plural": "Tentative Approval Message Template",
            },
        ),
    ]
