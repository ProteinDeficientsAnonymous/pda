import pytest
from community.models import JoinFormQuestion, JoinFormQuestionType, JoinRequest
from community.validation import Code
from django.core import mail

from tests._asserts import assert_error_code

PHONE = "+12025557777"


def _question(field_type=JoinFormQuestionType.CHECKBOX, required=True):
    return JoinFormQuestion.objects.create(
        label="how did you hear about us",
        field_type=field_type,
        options=["friend", "instagram"],
        required=required,
        display_order=99,
    )


def _submit(api_client, why_join_id, answers):
    return api_client.post(
        "/api/community/join-request/",
        {
            "first_name": "Leafy",
            "last_name": "G",
            "phone_number": PHONE,
            "email": "leafy@example.com",
            "answers": {why_join_id: "Liberation.", **answers},
            "sms_consent": True,
            "guidelines_consent": True,
        },
        content_type="application/json",
    )


@pytest.mark.django_db
class TestJoinRequestCheckboxAnswers:
    def test_list_answer_stored_deduped(self, api_client, why_join_id):
        q = _question()
        response = _submit(api_client, why_join_id, {str(q.id): ["friend", "instagram", "friend"]})
        assert response.status_code == 201
        jr = JoinRequest.objects.get(phone_number=PHONE)
        assert jr.custom_answers[str(q.id)]["answer"] == ["friend", "instagram"]

    def test_unknown_option_rejected(self, api_client, why_join_id):
        q = _question()
        response = _submit(api_client, why_join_id, {str(q.id): ["friend", "tiktok"]})
        assert_error_code(response, Code.JoinRequest.ANSWER_INVALID_OPTION)

    def test_required_empty_list_rejected(self, api_client, why_join_id):
        q = _question()
        response = _submit(api_client, why_join_id, {str(q.id): []})
        assert_error_code(response, Code.JoinRequest.ANSWER_REQUIRED)

    def test_list_answer_to_text_question_rejected(self, api_client, why_join_id):
        q = _question(field_type=JoinFormQuestionType.TEXT)
        response = _submit(api_client, why_join_id, {str(q.id): ["friend"]})
        assert_error_code(response, Code.JoinRequest.ANSWER_INVALID_FORMAT)

    def test_vetting_email_joins_ticked_options(self, api_client, why_join_id, settings):
        settings.VETTING_EMAIL = "vetting@pda.org"
        q = _question()
        _submit(api_client, why_join_id, {str(q.id): ["friend", "instagram"]})
        assert "how did you hear about us: friend, instagram" in mail.outbox[0].body

    def test_admin_list_returns_list_answer(self, api_client, why_join_id, vettor_headers):
        q = _question()
        _submit(api_client, why_join_id, {str(q.id): ["instagram"]})
        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        answers = response.json()[0]["answers"]
        assert {"question_id": str(q.id), "label": q.label, "answer": ["instagram"]} in answers
