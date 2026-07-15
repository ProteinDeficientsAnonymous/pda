from django.db import migrations


def seed_template(apps, schema_editor):
    MemberPromotionMessageTemplate = apps.get_model("community", "MemberPromotionMessageTemplate")
    MemberPromotionMessageTemplate.objects.get_or_create(pk=1)


def unseed_template(apps, schema_editor):
    MemberPromotionMessageTemplate = apps.get_model("community", "MemberPromotionMessageTemplate")
    MemberPromotionMessageTemplate.objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0074_memberpromotionmessagetemplate"),
    ]

    operations = [
        migrations.RunPython(seed_template, unseed_template),
    ]
