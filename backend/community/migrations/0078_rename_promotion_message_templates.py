from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0077_seed_membership_promotion_message"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="MemberPromotionMessageTemplate",
            new_name="MemberPromotionEmailTemplate",
        ),
        migrations.RenameModel(
            old_name="MembershipPromotionMessageTemplate",
            new_name="MemberPromotionMessageTemplate",
        ),
        migrations.AlterModelOptions(
            name="memberpromotionemailtemplate",
            options={
                "verbose_name": "Member Promotion Email Template",
                "verbose_name_plural": "Member Promotion Email Template",
            },
        ),
        migrations.AlterModelOptions(
            name="memberpromotionmessagetemplate",
            options={
                "verbose_name": "Member Promotion Message Template",
                "verbose_name_plural": "Member Promotion Message Template",
            },
        ),
    ]
