from unittest.mock import MagicMock

import pytest
from notifications.planning_email import (
    PlanningEmailDetails,
    PlanningEmailVariant,
    describe_slots,
    send_planning_email,
)


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        (("march",), "march"),
        (("march", "april"), "march and april"),
        (("march", "april", "may"), "march, april and may"),
        (("march", "april", "may", "june"), "4 slots"),
    ],
)
def test_describe_slots(labels, expected):
    assert describe_slots(labels) == expected


def _send(labels: tuple[str, ...], variant=PlanningEmailVariant.PROPOSED) -> dict:
    sender = MagicMock()
    details = PlanningEmailDetails(
        to="p@example.com",
        display_name="Sam",
        slot_labels=labels,
        planning_url="https://pda.test/admin/planning",
        variant=variant,
    )
    send_planning_email(sender=sender, details=details)
    return sender.send.call_args.kwargs


def test_one_slot_names_it_without_a_list():
    sent = _send(("March",))
    assert sent["subject"] == "can you plan march?"
    assert "any chance you could plan march? 🌱" in sent["text"]
    assert "<li>" not in sent["html"]
    assert "🌱\n\ntap below" in sent["text"]


def test_several_slots_go_in_one_email_listing_each():
    sent = _send(("March", "April", "May", "June"), PlanningEmailVariant.REMINDER)
    assert sent["subject"] == "still need an answer: can you plan 4 slots?"
    assert "just checking in — any chance you could plan 4 slots?" in sent["text"]
    for label in ("march", "april", "may", "june"):
        assert f"- {label}" in sent["text"]
        assert f"<li>{label}</li>" in sent["html"]
    assert "- june\n\ntap below" in sent["text"]
