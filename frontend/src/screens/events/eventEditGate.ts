import type { Event } from '@/models/event';
import { canManageEvent, EventStatus } from '@/models/event';
import type { User } from '@/models/user';

// grace period after an event ends so hosts can still fix typos or add follow-ups
const EDIT_GRACE_MS = 6 * 60 * 60 * 1000;

function isEditWindowOpen(event: Event): boolean {
  const reference = event.endDatetime ?? event.startDatetime;
  if (!reference) return true;
  return Date.now() <= reference.getTime() + EDIT_GRACE_MS;
}

// drafts have no published history to protect, so the edit-window cutoff doesn't apply
export function isEventEditable(event: Event): boolean {
  return event.status === EventStatus.Draft || isEditWindowOpen(event);
}

export function canEditEvent(event: Event, user: User | null): boolean {
  return canManageEvent(event, user) && isEventEditable(event);
}
