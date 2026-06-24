// Host "group text" helpers — the host's device sends; there's no server send
// (no sendable number, see #403).

import type { EventGuest } from '@/models/event';

export interface GroupTextRecipients {
  phones: string[]; // deduped, in guest order
  skippedCount: number; // guests with no usable number
}

// Guests with no number are excluded and counted so the UI can surface the skip.
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

// Comma-joined recipients open as one group thread on iOS and Android.
export function buildSmsUri(phones: string[]): string | null {
  if (phones.length === 0) return null;
  return `sms:${phones.join(',')}`;
}

// No feature detection exists for `sms:` handlers, so approximate via mobile UA.
export function isSmsSupported(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /android|iphone|ipad|ipod|mobile/i.test(navigator.userAgent);
}
