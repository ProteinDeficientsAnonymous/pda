import { parsePhoneNumberFromString } from 'libphonenumber-js';

export function formatPhone(raw: string): string {
  if (!raw) return raw;
  const parsed = parsePhoneNumberFromString(raw);
  if (!parsed) return raw;
  if (parsed.country === 'US') return parsed.formatNational();
  return parsed.formatInternational();
}
