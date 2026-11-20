import re

from django.db import migrations, models

_AMOUNT = re.compile(r"\$?(?:\d[\d,]*(?:\.\d+)?|\.\d+)")
_MAX_PRICE = 100000


def split_price(raw: str | None) -> tuple[str | None, str]:
    """return(tuple): the amount as numeric text (or None) and the leftover note."""
    raw = (raw or "").strip()
    amounts = _AMOUNT.findall(raw)
    if len(amounts) != 1:
        # Ranges ("$6-$8") and amount-free text ("pwyc") keep their wording as the note.
        return None, raw
    amount = amounts[0].lstrip("$").replace(",", "")
    if not 0 < float(amount) < _MAX_PRICE:
        return None, raw
    return amount, raw.replace(amounts[0], "", 1).strip(" -–—:,")


def to_numeric_text(apps, schema_editor):
    Event = apps.get_model("community", "Event")
    for event in Event.objects.exclude(price__isnull=True).only("id", "price"):
        event.price, event.price_note = split_price(event.price)
        event.save(update_fields=["price", "price_note"])


def to_blank_text(apps, schema_editor):
    apps.get_model("community", "Event").objects.filter(price__isnull=True).update(price="")


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0152_perf_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="price_note",
            field=models.CharField(max_length=100, blank=True, default=""),
            preserve_default=False,
        ),
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
