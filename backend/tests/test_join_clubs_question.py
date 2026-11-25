import importlib

import pytest
from community.join_requests.clubs_question import CLUBS_QUESTION_ID
from community.models import Club, JoinFormQuestion, JoinFormQuestionType, JoinRequest
from community.validation import Code
from django.apps import apps

from tests._asserts import assert_error_code

migration = importlib.import_module("community.migrations.0160_clubs_from_join_question")

PHONE = "+12025557777"
DOGS = "dog club (must be dog parent)"


@pytest.fixture
def clubs(db):
    Club.objects.create(name="book club")
    Club.objects.create(name="dog club", requirements="must be dog parent")


def _submit(api_client, why_join_id, answers):
    return api_client.post(
        "/api/community/join-request/",
        {
            "first_name": "Leafy",
            "phone_number": PHONE,
            "email": "leafy@example.com",
            "answers": {why_join_id: "Liberation.", **answers},
            "sms_consent": True,
            "guidelines_consent": True,
        },
        content_type="application/json",
    )


@pytest.mark.django_db
class TestJoinFormClubsQuestion:
    def test_last_and_managed_with_option_strings(self, api_client, clubs):
        JoinFormQuestion.objects.create(label="why", display_order=3)
        body = api_client.get("/api/community/join-form/").json()
        *real, built = body
        assert built["id"] == CLUBS_QUESTION_ID
        assert built["managed"] is True
        assert built["field_type"] == JoinFormQuestionType.CHECKBOX
        assert built["required"] is False
        assert built["options"] == ["book club", DOGS]
        assert built["display_order"] > max(q["display_order"] for q in real)
        assert all(q["managed"] is False for q in real)

    def test_absent_without_clubs(self, api_client, db):
        ids = [q["id"] for q in api_client.get("/api/community/join-form/").json()]
        assert CLUBS_QUESTION_ID not in ids


@pytest.mark.django_db
class TestSubmitClubsQuestion:
    def test_choices_set_interested_clubs_and_snapshot(self, api_client, why_join_id, clubs):
        response = _submit(api_client, why_join_id, {CLUBS_QUESTION_ID: ["book club", DOGS]})
        assert response.status_code == 201
        jr = JoinRequest.objects.get(phone_number=PHONE)
        assert set(jr.interested_clubs.values_list("name", flat=True)) == {"book club", "dog club"}
        assert jr.custom_answers[CLUBS_QUESTION_ID] == {
            "label": "which clubs are you interested in?",
            "answer": ["book club", DOGS],
        }

    def test_invalid_option_rejected(self, api_client, why_join_id, clubs):
        response = _submit(api_client, why_join_id, {CLUBS_QUESTION_ID: ["dog club"]})
        assert_error_code(response, Code.JoinRequest.ANSWER_INVALID_OPTION)
        assert not JoinRequest.objects.filter(phone_number=PHONE).exists()

    def test_unanswered_is_fine(self, api_client, why_join_id, clubs):
        assert _submit(api_client, why_join_id, {}).status_code == 201
        jr = JoinRequest.objects.get(phone_number=PHONE)
        assert not jr.interested_clubs.exists()
        assert CLUBS_QUESTION_ID not in jr.custom_answers


def _old_question(options):
    return JoinFormQuestion.objects.create(
        id=CLUBS_QUESTION_ID,
        label="which of the clubs are you interested in?",
        field_type=JoinFormQuestionType.CHECKBOX,
        options=options,
    )


def _request(phone, answer):
    return JoinRequest.objects.create(
        first_name="a",
        phone_number=phone,
        email=f"{phone[-4:]}@example.com",
        custom_answers={CLUBS_QUESTION_ID: {"label": "x", "answer": answer}},
    )


@pytest.mark.django_db
class TestClubsMigration:
    def test_noop_without_question(self):
        migration.forwards(apps, None)
        assert not Club.objects.exists()

    def test_creates_clubs_links_requests_and_drops_question(self):
        Club.objects.create(name="book club", requirements="kept")
        _old_question(["book club", "dog club (must be dog parent // guardian)", "plain"])
        both = _request("+12025550001", ["book club", "dog club (must be dog parent // guardian)"])
        text = _request("+12025550002", "plain")
        migration.forwards(apps, None)

        assert not JoinFormQuestion.objects.filter(id=CLUBS_QUESTION_ID).exists()
        assert Club.objects.get(name="book club").requirements == "kept"
        assert Club.objects.get(name="dog club").requirements == "must be dog parent // guardian"
        assert Club.objects.get(name="plain").requirements == ""
        assert Club.objects.count() == 3
        assert set(both.interested_clubs.values_list("name", flat=True)) == {
            "book club",
            "dog club",
        }
        assert not text.interested_clubs.exists()
