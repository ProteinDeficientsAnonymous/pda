from __future__ import annotations

from typing import TYPE_CHECKING

from .whatsapp import send_to_group

if TYPE_CHECKING:
    from community.models import Event


def notify_new_event(event: Event) -> bool:
    lines = [f"📅 New event: *{event.title}*"]

    start = event.start_datetime.strftime("%A, %B %-d at %-I:%M %p")
    end = event.end_datetime.strftime("%-I:%M %p")
    lines.append(f"🕐 {start} – {end}")

    if event.location:
        lines.append(f"📍 {event.location}")

    if event.description:
        lines.append(f"\n{event.description}")

    if event.partiful_link:
        lines.append(f"\nRSVP: {event.partiful_link}")
    elif event.whatsapp_link:
        lines.append(f"\nChat: {event.whatsapp_link}")
    elif event.other_link:
        lines.append(f"\nMore info: {event.other_link}")

    return send_to_group("\n".join(lines))


def admin_broadcast(message: str) -> bool:
    return send_to_group(message)
