import type { Event } from '@/models/event';
import { RsvpServerStatus } from '@/models/event';

// The recipient groups a host can pick when texting attendees. The four RSVP
// statuses come from each guest's `status`; `invited` covers invite-only
// members who haven't responded (their phones ride along on the event).
export const RecipientGroup = {
  Going: RsvpServerStatus.Attending,
  Maybe: RsvpServerStatus.Maybe,
  CantGo: RsvpServerStatus.CantGo,
  Waitlisted: RsvpServerStatus.Waitlisted,
  Invited: 'invited',
} as const;
export type RecipientGroupValue = (typeof RecipientGroup)[keyof typeof RecipientGroup];

export interface GroupTextRecipients {
  phones: string[];
  skippedCount: number;
}

export interface GroupOption {
  value: RecipientGroupValue;
  label: string;
  count: number;
}

const GROUP_LABELS: { value: RecipientGroupValue; label: string }[] = [
  { value: RecipientGroup.Going, label: 'going' },
  { value: RecipientGroup.Maybe, label: 'maybe' },
  { value: RecipientGroup.CantGo, label: "can't go" },
  { value: RecipientGroup.Waitlisted, label: 'waitlisted' },
  { value: RecipientGroup.Invited, label: 'invited' },
];

// How many people in this group have a textable number.
export function countForGroup(event: Event, value: RecipientGroupValue): number {
  if (value === RecipientGroup.Invited) {
    return event.invitedUserPhones.filter((p) => p?.trim()).length;
  }
  return event.guests.filter((g) => g.status === value && g.phone?.trim()).length;
}

// The groups worth offering — those with at least one reachable number.
export function availableGroups(event: Event): GroupOption[] {
  return GROUP_LABELS.map(({ value, label }) => ({
    value,
    label,
    count: countForGroup(event, value),
  })).filter((o) => o.count > 0);
}

// Pull deduped phone numbers for the selected groups. Guests (and invited
// members) with no number are counted as skipped so the UI can say so.
export function collectRecipients(
  event: Event,
  groups: Iterable<RecipientGroupValue>,
): GroupTextRecipients {
  const selected = new Set<RecipientGroupValue>(groups);
  const phones: string[] = [];
  const seen = new Set<string>();
  let skippedCount = 0;

  const add = (raw: string | null | undefined) => {
    const phone = raw?.trim();
    if (!phone) {
      skippedCount += 1;
      return;
    }
    if (seen.has(phone)) return;
    seen.add(phone);
    phones.push(phone);
  };

  for (const guest of event.guests) {
    if (selected.has(guest.status as RecipientGroupValue)) add(guest.phone);
  }
  if (selected.has(RecipientGroup.Invited)) {
    for (const phone of event.invitedUserPhones) add(phone);
  }

  return { phones, skippedCount };
}

// Apple platforms (macOS Messages + iOS) need the `sms:/open?addresses=`
// form to populate a MULTI-recipient group draft — a plain comma/semicolon
// list only picks up the first number. Non-Apple (Android) uses the plain
// `sms:` comma list, which `/open?addresses=` would break.
function isApplePlatform(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /iphone|ipad|ipod|macintosh|mac os x/i.test(navigator.userAgent);
}

export function buildSmsUri(phones: string[]): string | null {
  if (phones.length === 0) return null;
  const list = phones.join(',');
  return isApplePlatform() ? `sms:/open?addresses=${list}` : `sms:${list}`;
}
