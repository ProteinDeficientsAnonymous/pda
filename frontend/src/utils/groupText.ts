// Helpers for the host "group text" action — opens the host's own Messages app
// pre-populated with attendee phone numbers (issue #500). There is no server
// send (no sendable number — see #403); the host's device sends the message.
//
// On mobile the `sms:` URI scheme drops the host into a group thread with all
// recipients. On desktop (no `sms:` handler) we fall back to copying the
// comma-separated list so the host can paste it wherever they text from.

import type { EventGuest } from '@/models/event';

export interface GroupTextRecipients {
  // Deduped E.164 numbers, in guest order.
  phones: string[];
  // Count of guests in the chosen audience with no usable phone number.
  skippedCount: number;
}

// Default audience is everyone who RSVP'd, including "can't go" — they still
// want time/location/cancellation updates, matching the email blast (#499).
// Narrow the audience by filtering `guests` before passing them in. Guests with
// no number are excluded and counted so the UI can surface the skip.
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

// Comma-joined recipients are treated as one group thread by both iOS and
// Android. Returns null when empty so callers can disable the action.
export function buildSmsUri(phones: string[]): string | null {
  if (phones.length === 0) return null;
  return `sms:${phones.join(',')}`;
}

// There's no feature detection for `sms:` scheme handlers, so we approximate
// with a mobile-UA check: phones/tablets have a Messages app, desktops don't.
export function isSmsSupported(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /android|iphone|ipad|ipod|mobile/i.test(navigator.userAgent);
}
