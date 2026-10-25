from datetime import timedelta

from community.models import Event, EventType, JoinRequest, JoinRequestStatus
from django.utils import timezone
from users.models import User


def make_member(phone_number: str, **extra) -> User:
    extra.setdefault("email", f"{phone_number}@example.test")
    extra.setdefault("first_name", "Test")
    extra.setdefault("is_member", True)
    return User.objects.create_user(
        phone_number=phone_number,
        password="testpass123",
        **extra,
    )


def make_tentative(phone_number: str, **extra) -> User:
    user = User.objects.create(
        phone_number=phone_number,
        email=f"{phone_number}@example.test",
        first_name="Sprout",
        is_member=False,
        **extra,
    )
    JoinRequest.objects.create(
        first_name="Sprout",
        phone_number=phone_number,
        email=user.email,
        user=user,
        status=JoinRequestStatus.TENTATIVE,
    )
    return user


def make_event(title: str, days_out: float, **extra) -> Event:
    extra.setdefault("event_type", EventType.OFFICIAL)
    return Event.objects.create(
        title=title,
        start_datetime=timezone.now() + timedelta(days=days_out),
        location="the park",
        **extra,
    )
