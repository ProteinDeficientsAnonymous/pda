import type { Event } from '@/models/event';
import { canManageEvent, EventStatus } from '@/models/event';
import type { User } from '@/models/user';

// Editing stays open until 6 hours after the event's end (or start, if no end
// set) — gives hosts room to fix typos, post follow-ups, or tweak details
// during and right after the event without hitting a stale-data wall.
const EDIT_GRACE_MS = 6 * 60 * 60 * 1000;

function isEditWindowOpen(event: Event): boolean {
  const reference = event.endDatetime ?? event.startDatetime;
  if (!reference) return true;
  return Date.now() <= reference.getTime() + EDIT_GRACE_MS;
}

// Drafts are always editable — the edit-window cutoff protects the
// historical record of published events, which drafts don't have.
export function canEditEventWindow(event: Event): boolean {
  return event.status === EventStatus.Draft || isEditWindowOpen(event);
}

export function canEditEvent(event: Event, user: User | null): boolean {
  return canManageEvent(event, user) && canEditEventWindow(event);
}
