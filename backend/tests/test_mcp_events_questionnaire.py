import pytest
from community.models import EventRsvpQuestion, EventStatus, RsvpQuestionType, RSVPStatus

from tests._events import make_event, make_rsvp
from tests._mcp_members_helpers import make_member
from tests._mcp_tool_helpers import run_tool, tool_error
from tests._public_rsvp_helpers import make_public_rsvper

pytestmark = pytest.mark.django_db

TOOL = "event_questionnaire_responses"


def _answers(*pairs):
    return {str(q.id): {"label": q.label, "answer": a} for q, a in pairs}


@pytest.fixture
def event(test_user):
    return make_event(created_by=test_user, slug="photo-walk")


@pytest.fixture
def photo_question(event):
    return EventRsvpQuestion.objects.create(
        event=event,
        label="opt out of photos?",
        field_type=RsvpQuestionType.SELECT,
        options=["yes", "no"],
    )


def test_host_sees_answers_keyed_by_question_id(test_user, event, photo_question):
    note = EventRsvpQuestion.objects.create(
        event=event, label="anything else?", field_type=RsvpQuestionType.TEXTAREA, display_order=1
    )
    photo_id, note_id = str(photo_question.id), str(note.id)
    shy = make_member(last_name="Shy")
    guest = make_public_rsvper("+12025559101", "g@e.com", name="Pat Guest")
    make_rsvp(event, shy, questionnaire_responses=_answers((photo_question, "yes")))
    make_rsvp(
        event,
        guest,
        status=RSVPStatus.MAYBE,
        questionnaire_responses=_answers((photo_question, "no"), (note, "hi")),
    )
    make_rsvp(event, make_member(), status=RSVPStatus.REMOVED)

    body = run_tool(test_user, TOOL, event="photo-walk")

    assert body["event"]["id"] == str(event.id)
    assert [(q["id"], q["label"]) for q in body["questions"]] == [
        (photo_id, "opt out of photos?"),
        (note_id, "anything else?"),
    ]
    assert body["questions"][0]["options"] == ["yes", "no"]
    assert body["responses"] == [
        {
            "user_id": str(shy.id),
            "name": "M Shy",
            "is_member": True,
            "status": RSVPStatus.ATTENDING,
            "answers": {photo_id: "yes"},
        },
        {
            "user_id": str(guest.id),
            "name": "Pat Guest",
            "is_member": False,
            "status": RSVPStatus.MAYBE,
            "answers": {photo_id: "no", note_id: "hi"},
        },
    ]


def test_co_host_and_event_manager_can_read(event, photo_question, manage_events_user):
    co_host = make_member()
    event.co_hosts.add(co_host)
    make_rsvp(event, make_member(), questionnaire_responses=_answers((photo_question, "yes")))

    for user in (co_host, manage_events_user):
        body = run_tool(user, TOOL, event=str(event.id))
        assert body["responses"][0]["answers"] == {str(photo_question.id): "yes"}


def test_other_members_are_forbidden(event, photo_question):
    guest = make_member()
    make_rsvp(event, guest)
    assert "permission" in tool_error(guest, TOOL, event=str(event.id))


def test_unknown_or_deleted_event_is_an_error(test_user, event):
    assert tool_error(test_user, TOOL, event="nope") == "no event with that id or slug"
    event.status = EventStatus.DELETED
    event.save(update_fields=["status"])
    assert tool_error(test_user, TOOL, event=str(event.id)) == "no event with that id or slug"


def test_deleted_question_is_listed_from_its_snapshot(test_user, event, photo_question):
    gone = EventRsvpQuestion.objects.create(
        event=event, label="opt out of photos?", field_type=RsvpQuestionType.TEXTAREA
    )
    gone_id = str(gone.id)
    stored = _answers((gone, "old answer"), (photo_question, "no"))
    make_rsvp(event, make_member(), questionnaire_responses=stored)
    make_rsvp(event, make_member(), questionnaire_responses=_answers((gone, "also old")))
    gone.delete()

    body = run_tool(test_user, TOOL, event="photo-walk")

    assert body["questions"][1] == {"id": gone_id, "label": "opt out of photos?", "removed": True}
    assert len(body["questions"]) == 2
    assert [r["answers"] for r in body["responses"]] == [
        {str(photo_question.id): "no", gone_id: "old answer"},
        {gone_id: "also old"},
    ]


def test_malformed_snapshot_is_skipped(test_user, event, photo_question):
    stored = {**_answers((photo_question, "yes")), "legacy": "bare string"}
    make_rsvp(event, make_member(), questionnaire_responses=stored)

    body = run_tool(test_user, TOOL, event="photo-walk")

    assert len(body["questions"]) == 1
    assert body["responses"][0]["answers"] == {str(photo_question.id): "yes"}


def test_questions_sharing_a_label_keep_both_answers(test_user, event, photo_question):
    twin = EventRsvpQuestion.objects.create(
        event=event,
        label="opt out of photos?",
        field_type=RsvpQuestionType.TEXTAREA,
        display_order=1,
    )
    stored = _answers((twin, "only group shots"), (photo_question, "yes"))
    make_rsvp(event, make_member(), questionnaire_responses=stored)

    body = run_tool(test_user, TOOL, event="photo-walk")

    assert body["responses"][0]["answers"] == {
        str(photo_question.id): "yes",
        str(twin.id): "only group shots",
    }
