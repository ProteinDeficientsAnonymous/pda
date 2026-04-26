// Helpers for building "add to calendar" URLs and sharing an event.
//
// Google Calendar takes a structured URL; Apple Calendar + other clients
// consume an .ics file. The backend exposes `/api/community/events/{id}/ics/`
// so we link straight to that for Apple and also for the generic download.

import type { Event } from '@/models/event';

export function googleCalendarUrl(event: Event): string | null {
  if (!event.startDatetime) return null;
  const start = event.startDatetime;
  const end = event.endDatetime ?? new Date(start.getTime() + 2 * 60 * 60 * 1000);
  const dates = `${formatIcsDate(start)}/${formatIcsDate(end)}`;
  const details = buildDescription(event);
  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: event.title,
    dates,
  });
  if (details) params.set('details', details);
  if (event.location) params.set('location', event.location);
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

export function icsUrl(eventId: string): string {
  return `/api/community/events/${eventId}/ics/`;
}

// Apple Calendar single-event add: we used to use webcal:// here, but that's
// a *subscription* scheme — iOS/macOS treats the URL as an auto-refreshing
// feed and creates a calendar subscription, not a one-off add. For a single
// event that's the wrong UX. A plain https:// link to the .ics endpoint
// prompts the OS to open Calendar.app and add the event once.
export function appleCalendarUrl(eventId: string): string {
  const absolute = new URL(icsUrl(eventId), window.location.origin);
  return absolute.toString();
}

export async function shareEventUrl(event: Event): Promise<void> {
  const url = `${window.location.origin}/events/${event.id}`;
  const nav = window.navigator;
  const data: ShareData = { url, title: event.title };
  if (typeof nav.share === 'function' && nav.canShare(data)) {
    try {
      await nav.share(data);
      return;
    } catch (err) {
      // User cancelled the native sheet — don't fall through to clipboard.
      if (err instanceof Error && err.name === 'AbortError') return;
    }
  }
  await nav.clipboard.writeText(url);
}

// Mirrors backend `_event_ics_description` — both surfaces must end with a
// "View on PDA: <url>" line so users can jump from a calendar event back to
// the detail page (#347). If you change one, change the other.
function buildDescription(event: Event): string {
  const parts: string[] = [];
  if (event.description) parts.push(event.description);
  if (event.whatsappLink) parts.push(`WhatsApp: ${event.whatsappLink}`);
  if (event.partifulLink) parts.push(`Partiful: ${event.partifulLink}`);
  if (event.otherLink) parts.push(`Link: ${event.otherLink}`);
  parts.push(`View on PDA: ${window.location.origin}/events/${event.id}`);
  return parts.join('\n');
}

function formatIcsDate(d: Date): string {
  const y = d.getUTCFullYear().toString().padStart(4, '0');
  const m = (d.getUTCMonth() + 1).toString().padStart(2, '0');
  const day = d.getUTCDate().toString().padStart(2, '0');
  const h = d.getUTCHours().toString().padStart(2, '0');
  const min = d.getUTCMinutes().toString().padStart(2, '0');
  const s = d.getUTCSeconds().toString().padStart(2, '0');
  return `${y}${m}${day}T${h}${min}${s}Z`;
}
