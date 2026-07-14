from django.db import migrations


def seed_template(apps, schema_editor):
    TentativeApprovalMessageTemplate = apps.get_model(
        "community", "TentativeApprovalMessageTemplate"
    )
    TentativeApprovalMessageTemplate.objects.get_or_create(pk=1)


def unseed_template(apps, schema_editor):
    TentativeApprovalMessageTemplate = apps.get_model(
        "community", "TentativeApprovalMessageTemplate"
    )
    TentativeApprovalMessageTemplate.objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0071_tentativeapprovalmessagetemplate"),
    ]

    operations = [
        migrations.RunPython(seed_template, unseed_template),
    ]
