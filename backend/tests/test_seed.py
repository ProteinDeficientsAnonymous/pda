import pytest
from community.models import Event, EventRSVP, JoinRequest, RSVPStatus
from community.models.choices import AttendanceStatus
from django.core.management import call_command
from users.models import User


@pytest.mark.django_db
def test_seed_creates_expected_data():
    call_command("seed")

    assert User.objects.filter(phone_number="+17025550001").exists()
    assert User.objects.filter(phone_number="+17025550002").exists()
    assert Event.objects.count() == 5
    assert JoinRequest.objects.count() == 8


@pytest.mark.django_db
def test_seed_is_idempotent():
    call_command("seed")
    rsvp_count = EventRSVP.objects.count()
    call_command("seed")

    assert User.objects.filter(phone_number__startswith="+1702555").count() == 8
    assert Event.objects.count() == 5
    assert JoinRequest.objects.count() == 8
    assert EventRSVP.objects.count() == rsvp_count


@pytest.mark.django_db
def test_seed_creates_rsvps_with_all_statuses():
    call_command("seed")

    statuses = set(EventRSVP.objects.values_list("status", flat=True))
    assert statuses == {
        RSVPStatus.ATTENDING,
        RSVPStatus.MAYBE,
        RSVPStatus.CANT_GO,
        RSVPStatus.WAITLISTED,
    }


@pytest.mark.django_db
def test_seed_creates_full_event_with_waitlist():
    call_command("seed")

    event = Event.objects.get(title="Vegan Potluck")
    assert event.rsvp_enabled
    assert event.max_attendees == 3
    waitlisted = event.rsvps.filter(status=RSVPStatus.WAITLISTED).count()
    assert waitlisted >= 1


@pytest.mark.django_db
def test_seed_marks_attendance_on_past_event():
    call_command("seed")

    event = Event.objects.get(title="Past Potluck (seed)")
    marked = event.rsvps.filter(
        attendance__in=[AttendanceStatus.ATTENDED, AttendanceStatus.NO_SHOW]
    )
    assert marked.filter(attendance=AttendanceStatus.ATTENDED).exists()
    assert marked.filter(attendance=AttendanceStatus.NO_SHOW).exists()


@pytest.mark.django_db
def test_seed_creates_plus_one_rsvps():
    call_command("seed")

    assert EventRSVP.objects.filter(has_plus_one=True).exists()


@pytest.mark.django_db
def test_seed_admin_has_superuser_privileges():
    call_command("seed")

    admin = User.objects.get(phone_number="+17025550001")
    assert admin.is_superuser
    assert admin.is_staff
    assert admin.roles.filter(name="admin").exists()
