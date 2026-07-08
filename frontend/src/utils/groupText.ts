import type { EventGuest } from '@/models/event';

export interface GroupTextRecipients {
  phones: string[];
  skippedCount: number;
}

export function collectRecipients(guests: EventGuest[]): GroupTextRecipients {
  const phones: string[] = [];
  const seen = new Set<string>();
  let skippedCount = 0;
  for (const guest of guests) {
    const phone = guest.phone?.trim();
    if (!phone) {
      skippedCount += 1;
      continue;
    }
    if (seen.has(phone)) continue;
    seen.add(phone);
    phones.push(phone);
  }
  return { phones, skippedCount };
}

export function buildSmsUri(phones: string[]): string | null {
  if (phones.length === 0) return null;
  return `sms:${phones.join(',')}`;
}

export function isSmsSupported(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /android|iphone|ipad|ipod|mobile/i.test(navigator.userAgent);
}
