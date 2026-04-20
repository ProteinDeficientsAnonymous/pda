from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0042_eventflag"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("active", "Active"),
                    ("cancelled", "Cancelled"),
                    ("deleted", "Deleted"),
                ],
                default="active",
                max_length=20,
            ),
        ),
    ]
