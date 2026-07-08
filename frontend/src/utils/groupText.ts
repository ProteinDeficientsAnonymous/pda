import type { TextRecipients } from '@/api/textRecipients';

// The recipient groups a host can pick when texting attendees. Each value is a
// key into the host-only TextRecipients payload fetched from the backend.
export const RecipientGroup = {
  Going: 'attending',
  Maybe: 'maybe',
  CantGo: 'cantGo',
  Waitlisted: 'waitlisted',
  Invited: 'invited',
} as const;
export type RecipientGroupValue = (typeof RecipientGroup)[keyof typeof RecipientGroup];

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

// The groups worth offering — those with at least one reachable number.
export function availableGroups(recipients: TextRecipients): GroupOption[] {
  return GROUP_LABELS.map(({ value, label }) => ({
    value,
    label,
    count: recipients[value].length,
  })).filter((o) => o.count > 0);
}

// Deduped phone numbers for the selected groups. A number can appear in more
// than one group (e.g. an invited member who also RSVP'd) — dedupe so it isn't
// texted twice.
export function collectPhones(
  recipients: TextRecipients,
  groups: Iterable<RecipientGroupValue>,
): string[] {
  const phones: string[] = [];
  const seen = new Set<string>();
  for (const group of groups) {
    for (const phone of recipients[group]) {
      if (seen.has(phone)) continue;
      seen.add(phone);
      phones.push(phone);
    }
  }
  return phones;
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
