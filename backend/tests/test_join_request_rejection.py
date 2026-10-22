import pytest
from community._validation import Code
from community.models import JoinRequestStatus, RejectionEmailTemplate, RejectionReason

from tests._asserts import assert_error_code


def _reject(api_client, headers, join_request, **extra):
    return api_client.patch(
        f"/api/community/join-requests/{join_request.id}/",
        {"status": JoinRequestStatus.REJECTED, **extra},
        content_type="application/json",
        **headers,
    )


def _sends_to(fake_email_sender, to):
    return [c.kwargs for c in fake_email_sender.send.call_args_list if c.kwargs["to"] == to]


@pytest.fixture
def applicant(sample_join_request):
    sample_join_request.email = "applicant@example.com"
    sample_join_request.save(update_fields=["email"])
    return sample_join_request


@pytest.mark.django_db
class TestRejectWithReason:
    def test_preset_reason_is_stored_and_emailed(
        self, api_client, vettor_headers, applicant, fake_email_sender
    ):
        response = _reject(
            api_client, vettor_headers, applicant, rejection_reason=RejectionReason.VEGETARIAN
        )
        assert response.status_code == 200
        applicant.refresh_from_db()
        assert applicant.rejection_reason == RejectionReason.VEGETARIAN
        assert applicant.rejection_note == ""

        sends = _sends_to(fake_email_sender, "applicant@example.com")
        assert len(sends) == 1
        assert RejectionEmailTemplate.get().vegetarian_text in sends[0]["text"]
        assert "${REASON}" not in sends[0]["text"]

    def test_edited_reason_text_is_used(
        self, api_client, vettor_headers, applicant, fake_email_sender
    ):
        template = RejectionEmailTemplate.get()
        template.body = "hey ${FIRST_NAME}. ${REASON}"
        template.not_vegan_text = "custom not vegan copy"
        template.save()

        _reject(api_client, vettor_headers, applicant, rejection_reason=RejectionReason.NOT_VEGAN)

        text = _sends_to(fake_email_sender, "applicant@example.com")[0]["text"]
        assert "hey Sprout. custom not vegan copy" in text

    def test_other_reason_emails_the_note(
        self, api_client, vettor_headers, applicant, fake_email_sender
    ):
        _reject(
            api_client,
            vettor_headers,
            applicant,
            rejection_reason=RejectionReason.OTHER,
            rejection_note="  we're at capacity right now  ",
        )
        applicant.refresh_from_db()
        assert applicant.rejection_note == "we're at capacity right now"
        text = _sends_to(fake_email_sender, "applicant@example.com")[0]["text"]
        assert "we're at capacity right now" in text

    def test_no_reason_still_emails_without_placeholder(
        self, api_client, vettor_headers, applicant, fake_email_sender
    ):
        response = _reject(api_client, vettor_headers, applicant)
        assert response.status_code == 200
        applicant.refresh_from_db()
        assert applicant.rejection_reason == ""
        sends = _sends_to(fake_email_sender, "applicant@example.com")
        assert len(sends) == 1
        assert "${REASON}" not in sends[0]["text"]
        assert "\n\n\n" not in sends[0]["text"].split("— pda")[0]

    def test_note_dropped_for_preset_reason(self, api_client, vettor_headers, applicant):
        _reject(
            api_client,
            vettor_headers,
            applicant,
            rejection_reason=RejectionReason.QUESTIONS_NOT_ANSWERED,
            rejection_note="stray",
        )
        applicant.refresh_from_db()
        assert applicant.rejection_note == ""

    def test_other_without_note_is_rejected(
        self, api_client, vettor_headers, applicant, fake_email_sender
    ):
        response = _reject(
            api_client, vettor_headers, applicant, rejection_reason=RejectionReason.OTHER
        )
        assert response.status_code == 422
        assert_error_code(response, Code.JoinRequest.REJECTION_NOTE_REQUIRED, "rejection_note")
        applicant.refresh_from_db()
        assert applicant.status == JoinRequestStatus.PENDING
        assert fake_email_sender.send.call_count == 0

    def test_note_too_long_is_rejected(self, api_client, vettor_headers, applicant):
        response = _reject(
            api_client,
            vettor_headers,
            applicant,
            rejection_reason=RejectionReason.OTHER,
            rejection_note="x" * 1001,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.JoinRequest.REJECTION_NOTE_TOO_LONG, "rejection_note")

    def test_unknown_reason_is_rejected(self, api_client, vettor_headers, applicant):
        response = _reject(api_client, vettor_headers, applicant, rejection_reason="rude")
        assert response.status_code == 422
        assert_error_code(response, Code.JoinRequest.INVALID_REJECTION_REASON, "rejection_reason")

    def test_reason_ignored_for_non_rejection(
        self, api_client, vettor_headers, applicant, fake_email_sender
    ):
        response = api_client.patch(
            f"/api/community/join-requests/{applicant.id}/",
            {"status": JoinRequestStatus.TENTATIVE, "rejection_reason": "rude"},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        applicant.refresh_from_db()
        assert applicant.rejection_reason == ""
        assert _sends_to(fake_email_sender, "applicant@example.com") == []

    def test_no_email_on_file_skips_send(
        self, api_client, vettor_headers, sample_join_request, fake_email_sender
    ):
        response = _reject(api_client, vettor_headers, sample_join_request)
        assert response.status_code == 200
        assert fake_email_sender.send.call_count == 0

    def test_send_failure_does_not_roll_back(
        self, api_client, vettor_headers, applicant, fake_email_sender
    ):
        fake_email_sender.send.side_effect = RuntimeError("provider down")
        response = _reject(api_client, vettor_headers, applicant)
        assert response.status_code == 200
        applicant.refresh_from_db()
        assert applicant.status == JoinRequestStatus.REJECTED

    def test_list_exposes_reason(self, api_client, vettor_headers, applicant):
        _reject(api_client, vettor_headers, applicant, rejection_reason=RejectionReason.VEGETARIAN)
        rows = api_client.get("/api/community/join-requests/", **vettor_headers).json()
        row = next(r for r in rows if r["id"] == str(applicant.id))
        assert row["rejection_reason"] == RejectionReason.VEGETARIAN

    def test_unreject_clears_reason(self, api_client, vettor_headers, applicant):
        _reject(
            api_client,
            vettor_headers,
            applicant,
            rejection_reason=RejectionReason.OTHER,
            rejection_note="note",
        )
        response = api_client.patch(
            f"/api/community/join-requests/{applicant.id}/unreject/",
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        assert response.json()["rejection_reason"] == ""
        assert response.json()["rejection_note"] == ""
