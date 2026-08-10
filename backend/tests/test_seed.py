import pytest
from community.management.commands._seed_data import SEED_EVENT_RSVP_QUESTIONS
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
        attendance__in=[AttendanceStatus.ATTENDED, AttendanceStatus.DIDNT_GO]
    )
    assert marked.filter(attendance=AttendanceStatus.ATTENDED).exists()
    assert marked.filter(attendance=AttendanceStatus.DIDNT_GO).exists()


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


@pytest.mark.django_db
def test_seed_creates_rsvp_questions_on_configured_events():
    call_command("seed")

    for title, specs in SEED_EVENT_RSVP_QUESTIONS.items():
        event = Event.objects.get(title=title)
        labels = list(
            event.rsvp_questions.order_by("display_order").values_list("label", flat=True)
        )
        assert labels == [spec.label for spec in specs]


@pytest.mark.django_db
def test_seed_rsvps_include_partial_and_complete_questionnaire_responses():
    call_command("seed")

    event = Event.objects.get(title="Plant-Based Cooking Workshop")
    questions = {q.label: q for q in event.rsvp_questions.all()}
    assert len(questions) == 2

    complete = EventRSVP.objects.get(event=event, user__phone_number="+17025550002")
    assert set(complete.questionnaire_responses) == {str(q.id) for q in questions.values()}
    assert {
        snap["label"]: snap["answer"] for snap in complete.questionnaire_responses.values()
    } == {
        "How are you getting there?": "transit",
        "Anything we should know?": "Nut allergy — please avoid shared utensils.",
    }

    partial = EventRSVP.objects.get(event=event, user__phone_number="+17025550003")
    assert set(partial.questionnaire_responses) == {str(questions["How are you getting there?"].id)}
    assert (
        partial.questionnaire_responses[str(questions["How are you getting there?"].id)]["answer"]
        == "bike"
    )

    unanswered = EventRSVP.objects.get(event=event, user__phone_number="+17025550004")
    assert unanswered.questionnaire_responses == {}
