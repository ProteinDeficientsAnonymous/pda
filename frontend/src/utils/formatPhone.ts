// Format a phone number for display. US numbers render as `(xxx) xxx-xxxx`
// (country code dropped since the user base is primarily US); everything else
// falls back to the international format (`+44 20 7946 0958`). Invalid or
// empty input passes through unchanged so we never hide data from admins.

import { parsePhoneNumberFromString } from 'libphonenumber-js';

export function formatPhone(raw: string): string {
  if (!raw) return raw;
  const parsed = parsePhoneNumberFromString(raw);
  if (!parsed) return raw;
  if (parsed.country === 'US') return parsed.formatNational();
  return parsed.formatInternational();
}
