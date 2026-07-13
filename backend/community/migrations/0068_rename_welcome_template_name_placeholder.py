from django.db import migrations

OLD_TOKEN = "${NAME}"
NEW_TOKEN = "${FIRST_NAME}"


def rename_token(apps, schema_editor):
    WelcomeMessageTemplate = apps.get_model("community", "WelcomeMessageTemplate")
    for template in WelcomeMessageTemplate.objects.all().iterator():
        if OLD_TOKEN in template.body:
            template.body = template.body.replace(OLD_TOKEN, NEW_TOKEN)
            template.save(update_fields=["body"])


def revert_token(apps, schema_editor):
    WelcomeMessageTemplate = apps.get_model("community", "WelcomeMessageTemplate")
    for template in WelcomeMessageTemplate.objects.all().iterator():
        if NEW_TOKEN in template.body:
            template.body = template.body.replace(NEW_TOKEN, OLD_TOKEN)
            template.save(update_fields=["body"])


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0067_remove_joinrequest_display_name"),
    ]
    operations = [migrations.RunPython(rename_token, revert_token)]
