from unittest.mock import MagicMock

import pytest
from community.models import ClubReminderStage
from notifications.club_reminder_email import ClubReminderEmailDetails, send_club_reminder_email


def _send(stage, share_passed=False):
    sender = MagicMock()
    details = ClubReminderEmailDetails(
        to="a@example.test",
        display_name="a",
        club_name="Book Club",
        month_label="december",
        deadline_label="nov 30",
        stage=stage,
        create_url="https://x.test/events/add",
        share_passed=share_passed,
    )
    send_club_reminder_email(sender=sender, details=details)
    return sender.send.call_args.kwargs


@pytest.mark.parametrize(
    ("stage", "share_passed", "subject", "phrases"),
    [
        (
            ClubReminderStage.EARLY,
            False,
            "december book club events get shared on the 15th",
            ["shared in the whatsapp on the 15th", "due by nov 30"],
        ),
        (
            ClubReminderStage.EARLY,
            True,
            "book club: december events due by nov 30",
            ["due by nov 30"],
        ),
        (
            ClubReminderStage.WEEK,
            False,
            "book club: december events due by nov 30",
            ["due by nov 30"],
        ),
        (
            ClubReminderStage.FINAL,
            False,
            "book club: december events due today",
            ["due today"],
        ),
    ],
)
def test_subject_and_body(stage, share_passed, subject, phrases):
    sent = _send(stage, share_passed)
    assert sent["subject"] == subject
    for phrase in phrases:
        assert phrase in sent["text"]


def test_early_after_share_omits_the_15th_line():
    assert "on the 15th" not in _send(ClubReminderStage.EARLY, True)["text"]
