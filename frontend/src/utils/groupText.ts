import type { TextRecipients } from '@/api/textRecipients';

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

export function availableGroups(recipients: TextRecipients): GroupOption[] {
  return GROUP_LABELS.map(({ value, label }) => ({
    value,
    label,
    count: recipients[value].length,
  })).filter((o) => o.count > 0);
}

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

function isApplePlatform(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /iphone|ipad|ipod|macintosh|mac os x/i.test(navigator.userAgent);
}

export function buildSmsUri(phones: string[]): string | null {
  if (phones.length === 0) return null;
  const list = phones.join(',');
  return isApplePlatform() ? `sms:/open?addresses=${list}` : `sms:${list}`;
}
