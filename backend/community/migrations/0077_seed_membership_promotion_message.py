from django.db import migrations


def seed_template(apps, schema_editor):
    MembershipPromotionMessageTemplate = apps.get_model(
        "community", "MembershipPromotionMessageTemplate"
    )
    MembershipPromotionMessageTemplate.objects.get_or_create(pk=1)


def unseed_template(apps, schema_editor):
    MembershipPromotionMessageTemplate = apps.get_model(
        "community", "MembershipPromotionMessageTemplate"
    )
    MembershipPromotionMessageTemplate.objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0076_membershippromotionmessagetemplate_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_template, unseed_template),
    ]
