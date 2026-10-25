import pytest
from community.management.commands._seed_staging_data import perm_phone
from community.models import Event, EventComment
from django.core.management import call_command
from users.models import User


@pytest.mark.django_db
def test_seed_staging_reset_deletes_seeded_users_comments_on_real_events(test_user):
    call_command("seed_staging")
    real_event = Event.objects.create(
        title="real event", start_datetime="2030-01-01T00:00:00Z", created_by=test_user
    )
    seeded_user = User.objects.get(phone_number=perm_phone(0))
    EventComment.objects.create(event=real_event, author=seeded_user, body="from staging")
    real_comment = EventComment.objects.create(event=real_event, author=test_user, body="mine")

    call_command("seed_staging", "--reset")

    assert not EventComment.objects.filter(body="from staging").exists()
    assert EventComment.objects.filter(pk=real_comment.pk).exists()
    assert Event.objects.filter(pk=real_event.pk).exists()
    assert User.objects.get(phone_number=perm_phone(0)).pk != seeded_user.pk
