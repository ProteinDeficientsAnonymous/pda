from unittest.mock import MagicMock

from community._host_digest import EventDigest
from notifications._host_digest_email import send_host_digest_email
from notifications.email_sender import SendResult

SETTINGS_URL = "https://pda.test/settings"
EVENT_URL = "https://pda.test/events/south-mountain-hike-2"


def _event(**overrides) -> EventDigest:
    fields = {
        "title": "South Mountain Hike",
        "when": "saturday, october 18 at 10:00 am",
        "url": EVENT_URL,
        "capacity_line": "12/12 going · full · 3 waitlisted",
        "rsvp_groups": [("going", ["sam", "alex"]), ("can't go", ["chris"])],
        "new_comment_count": 3,
    }
    return EventDigest(**{**fields, **overrides})


def _send(events: list[EventDigest], display_name: str = "Leah") -> dict:
    sender = MagicMock()
    sender.send.return_value = SendResult(success=True, provider_message_id="m1")
    result = send_host_digest_email(
        sender=sender,
        to="host@example.test",
        display_name=display_name,
        events=events,
        settings_url=SETTINGS_URL,
    )
    assert result.success is True
    sender.send.assert_called_once()
    return sender.send.call_args.kwargs


def _assert_in_order(body: str, parts: list[str]) -> None:
    position = 0
    for part in parts:
        found = body.find(part, position)
        assert found != -1, f"{part!r} missing or out of order in:\n{body}"
        position = found + len(part)


class TestSendHostDigestEmail:
    def test_text_body_lists_event(self):
        kwargs = _send([_event()])
        assert kwargs["subject"] == "what's new on your events"
        assert kwargs["to"] == "host@example.test"
        _assert_in_order(
            kwargs["text"],
            [
                "hi leah —",
                "here's what happened on your events:",
                "south mountain hike",
                "saturday, october 18 at 10:00 am",
                "12/12 going · full · 3 waitlisted",
                "going: sam, alex",
                "can't go: chris",
                "3 new comments",
                EVENT_URL,
                "update your preferences",
                SETTINGS_URL,
                "this is an automated email",
            ],
        )

    def test_html_body_lists_event(self):
        html = _send([_event()])["html"]
        _assert_in_order(
            html,
            [
                "hi leah —",
                "here's what happened on your events:",
                "south mountain hike",
                "saturday, october 18 at 10:00 am",
                "12/12 going · full · 3 waitlisted",
                "going: sam, alex",
                "can&#x27;t go: chris",
                "3 new comments",
                f'href="{EVENT_URL}"',
                "view event",
                f'href="{SETTINGS_URL}"',
                "update your preferences",
                "this is an automated email",
            ],
        )

    def test_comment_line_singular_or_omitted(self):
        one, zero = _send([_event(new_comment_count=1)]), _send([_event(new_comment_count=0)])
        for body in (one["text"], one["html"]):
            assert "1 new comment" in body
            assert "1 new comments" not in body
        assert "new comment" not in zero["text"] + zero["html"]

    def test_comment_only_event_has_no_group_lines(self):
        kwargs = _send([_event(rsvp_groups=[], new_comment_count=2)])
        for body in (kwargs["text"], kwargs["html"]):
            assert "2 new comments" in body
            assert "going:" not in body

    def test_multiple_events_render_in_order(self):
        other_url = "https://pda.test/events/potluck"
        potluck = _event(
            title="Potluck", url=other_url, capacity_line="4 going", rsvp_groups=[("maybe", ["jo"])]
        )
        kwargs = _send([_event(), potluck])
        for body in (kwargs["text"], kwargs["html"]):
            _assert_in_order(
                body,
                ["south mountain hike", EVENT_URL, "potluck", "4 going", "maybe: jo", other_url],
            )

    def test_title_and_names_escaped_in_html_and_raw_in_text(self):
        groups = [("going", ["sam & co", "<b>x</b>"])]
        kwargs = _send([_event(title="mac & cheese <3", rsvp_groups=groups)])
        assert "mac & cheese <3" in kwargs["text"]
        assert "going: sam & co, <b>x</b>" in kwargs["text"]
        assert "mac &amp; cheese &lt;3" in kwargs["html"]
        assert "going: sam &amp; co, &lt;b&gt;x&lt;/b&gt;" in kwargs["html"]

    def test_dynamic_copy_is_lowercased(self):
        when = "Saturday, October 18 at 10:00 AM"
        kwargs = _send([_event(when=when, rsvp_groups=[("going", ["Sam", "ALEX"])])])
        assert kwargs["text"] == kwargs["text"].lower()
        for part in ("going: sam, alex", when.lower(), "hi leah —"):
            assert part in kwargs["html"]

    def test_blank_display_name_still_greets(self):
        kwargs = _send([_event()], display_name="")
        assert kwargs["text"].startswith("hi —")
        assert "hi —" in kwargs["html"]
