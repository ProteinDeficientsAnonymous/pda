from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0055_user_attendance_pause"),
    ]

    operations = [
        migrations.RenameModel(old_name="NonMemberRsvpToken", new_name="PublicRsvpToken"),
    ]
