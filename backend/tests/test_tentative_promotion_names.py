import pytest
from audit.models import AuditLogEntry
from community.join_requests import check_in_promotion
from community.models import AttendanceStatus, EventRSVP, JoinRequestStatus
from django.utils import timezone
from users.models import MembershipStatus, User

from tests._tentative_helpers import (
    check_in,
    decide,
    open_official_event,
    tentative_user_with_rsvp,
)
from tests._users import make_user

__all__ = ["open_official_event"]

pytestmark = pytest.mark.django_db

PHONE = "+16505551234"
STALE_NAME = "rsvp guest 2"


@pytest.fixture
def stale_tentative(sample_join_request, vettor_user, open_official_event):
    """Tentative under an old public-rsvp name that fails display-name validation."""
    user = tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
    User.objects.filter(pk=user.pk).update(first_name=STALE_NAME, last_name="")
    return user


@pytest.mark.parametrize("archived", [False, True])
def test_tentative_takes_the_join_form_name(
    api_client, vettor_headers, sample_join_request, archived
):
    archive = {
        "membership_status": MembershipStatus.ARCHIVED,
        "status_before_archive": MembershipStatus.NONE,
        "archived_at": timezone.now(),
    }
    existing = make_user(
        phone_number=PHONE,
        first_name="Rsvp",
        last_name="Guest",
        **(archive if archived else {"membership_status": MembershipStatus.NONE}),
    )
    resp = decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    assert resp.status_code == 200
    existing.refresh_from_db()
    assert existing.membership_status == MembershipStatus.TENTATIVE
    assert (existing.first_name, existing.last_name) == ("Sprout", "Seedling")


def test_check_in_promotes_without_touching_the_name(
    api_client, stale_tentative, open_official_event, fake_email_sender
):
    resp = check_in(api_client, open_official_event, stale_tentative)
    assert resp.status_code == 200
    stale_tentative.refresh_from_db()
    assert stale_tentative.is_member is True
    assert stale_tentative.first_name == STALE_NAME


def test_manual_approve_promotes_without_touching_the_name(
    api_client, vettor_headers, stale_tentative, sample_join_request, fake_email_sender
):
    resp = decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)
    assert resp.status_code == 200
    stale_tentative.refresh_from_db()
    assert stale_tentative.is_member is True
    assert stale_tentative.first_name == STALE_NAME


@pytest.fixture
def failing_promotion(monkeypatch):
    def fail(*_args, **_kwargs):
        raise RuntimeError("promotion failed")

    monkeypatch.setattr(check_in_promotion, "maybe_promote_tentative", fail)


@pytest.mark.usefixtures("failing_promotion")
def test_failed_promotion_keeps_the_check_in(
    api_client,
    stale_tentative,
    open_official_event,
    fake_email_sender,
    django_capture_on_commit_callbacks,
):
    join_request = stale_tentative.join_requests.get()
    with django_capture_on_commit_callbacks(execute=True):
        resp = check_in(api_client, open_official_event, stale_tentative)
    assert resp.status_code == 200
    rsvp = EventRSVP.objects.get(event=open_official_event, user=stale_tentative)
    assert rsvp.attendance == AttendanceStatus.ATTENDED
    assert rsvp.checked_in_at is not None
    stale_tentative.refresh_from_db()
    join_request.refresh_from_db()
    assert stale_tentative.membership_status == MembershipStatus.TENTATIVE
    assert join_request.status == JoinRequestStatus.TENTATIVE
    assert AuditLogEntry.objects.filter(
        action="check_in_promotion_failed", target_id=str(stale_tentative.pk)
    ).exists()
    fake_email_sender.send.assert_not_called()
