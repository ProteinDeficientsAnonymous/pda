import json

import pytest
from community.models import Event, EventRSVP
from django.core.management import call_command
from django.core.management.base import CommandError
from users.models import NonMemberRsvpToken, User


@pytest.mark.django_db
def test_e2e_seed_member(capsys):
    call_command("e2e_seed", "member")
    out = json.loads(capsys.readouterr().out)
    assert Event.objects.filter(id=out["event_id"]).exists()
    user = User.objects.get(phone_number=out["user_phone"])
    assert user.is_member is True
    assert user.check_password(out["user_password"])
    assert out["access_token"]


@pytest.mark.django_db
def test_e2e_seed_public_new(capsys):
    call_command("e2e_seed", "public-new")
    out = json.loads(capsys.readouterr().out)
    assert Event.objects.filter(id=out["event_id"]).exists()
    assert set(out.keys()) == {"event_id", "event_title", "event_location"}


@pytest.mark.django_db
def test_e2e_seed_public_returning(capsys):
    call_command("e2e_seed", "public-returning")
    out = json.loads(capsys.readouterr().out)
    user = User.objects.get(phone_number=out["user_phone"])
    assert EventRSVP.objects.filter(event_id=out["event_id"], user=user).exists()
    assert NonMemberRsvpToken.resolve_user(out["rsvp_token"]) == user


@pytest.mark.django_db
def test_e2e_seed_comments(capsys):
    call_command("e2e_seed", "comments")
    out = json.loads(capsys.readouterr().out)
    assert NonMemberRsvpToken.resolve_user(out["rsvp_token"]) is not None
    assert EventRSVP.objects.filter(event_id=out["event_id"]).exists()


@pytest.mark.django_db
def test_e2e_seed_my_rsvps(capsys):
    call_command("e2e_seed", "my-rsvps")
    out = json.loads(capsys.readouterr().out)
    assert NonMemberRsvpToken.resolve_user(out["rsvp_token"]) is not None


@pytest.mark.django_db
def test_e2e_seed_live_updates(capsys):
    call_command("e2e_seed", "live-updates")
    out = json.loads(capsys.readouterr().out)
    for key in ("user_a_phone", "user_a_password", "user_b_phone", "user_b_password"):
        assert out[key]
    assert User.objects.get(phone_number=out["user_a_phone"]).is_member is True
    assert User.objects.get(phone_number=out["user_b_phone"]).is_member is True


@pytest.mark.django_db
def test_e2e_seed_unknown_scenario():
    with pytest.raises(CommandError):
        call_command("e2e_seed", "not-a-real-scenario")
