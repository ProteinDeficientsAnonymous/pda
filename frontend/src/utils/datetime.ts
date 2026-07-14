// Date formatting helpers. Centralized so Event rendering stays consistent
// across calendar, detail panel, and list views.

import { format, isSameDay } from 'date-fns';

export function formatEventDateTime(
  start: Date | null,
  end: Date | null,
  datetimeTbd = false,
): string {
  if (datetimeTbd || !start) return 'date & time tbd';
  const startStr = format(start, 'EEE MMM d, h:mm a').toLowerCase();
  if (!end) return startStr;
  if (isSameDay(start, end)) {
    return `${startStr} – ${format(end, 'h:mm a').toLowerCase()}`;
  }
  return `${startStr} → ${format(end, 'EEE MMM d, h:mm a').toLowerCase()}`;
}

export function formatDayHeader(date: Date): string {
  return format(date, 'EEEE, MMMM d');
}

export function parseIsoDate(iso: string): Date {
  // Backend serializes DateTimeField as ISO 8601 with timezone; Date constructor
  // parses that natively.
  return new Date(iso);
}

export function formatBirthday(isoDate: string): string {
  // A birthday is a plain yyyy-mm-dd with no timezone. `new Date('yyyy-mm-dd')`
  // parses as UTC midnight, which shifts the day in negative-offset zones, so
  // build a local date from the parts instead.
  const [year, month, day] = isoDate.split('-').map(Number);
  if (!year || !month || !day) return '';
  return format(new Date(year, month - 1, day), 'MMMM d, yyyy').toLowerCase();
}
