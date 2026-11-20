import re

from django.db import migrations, models

_FIRST_NUMBER = re.compile(r"\d+(?:\.\d+)?|\.\d+")
_MAX_PRICE = 100000


def numeric_text(raw: str | None) -> str | None:
    # Prod only had past free-text prices ("$10 deposit", "~$35 - ~$60 sliding scale"); keep the first amount.
    match = _FIRST_NUMBER.search((raw or "").replace(",", ""))
    # Out-of-range amounts (e.g. a phone number) would overflow numeric(8,2) and abort the migration.
    return match.group(0) if match and 0 < float(match.group(0)) < _MAX_PRICE else None


def to_numeric_text(apps, schema_editor):
    Event = apps.get_model("community", "Event")
    for event in Event.objects.exclude(price__isnull=True).only("id", "price"):
        event.price = numeric_text(event.price)
        event.save(update_fields=["price"])


def to_blank_text(apps, schema_editor):
    apps.get_model("community", "Event").objects.filter(price__isnull=True).update(price="")


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0152_perf_indexes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="price",
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.RunPython(to_numeric_text, to_blank_text),
        migrations.AlterField(
            model_name="event",
            name="price",
            field=models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True),
        ),
    ]
