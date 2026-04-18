// Date formatting helpers. Centralized so Event rendering stays consistent
// across calendar, detail panel, and list views.

import { format, isSameDay } from 'date-fns';

export function formatEventDateTime(start: Date, end: Date | null, datetimeTbd = false): string {
  if (datetimeTbd) return 'date & time tbd';
  const startStr = format(start, 'EEE MMM d, h:mm a');
  if (!end) return startStr;
  if (isSameDay(start, end)) {
    return `${startStr} – ${format(end, 'h:mm a')}`;
  }
  return `${startStr} → ${format(end, 'EEE MMM d, h:mm a')}`;
}

export function formatDayHeader(date: Date): string {
  return format(date, 'EEEE, MMMM d');
}

export function parseIsoDate(iso: string): Date {
  // Backend serializes DateTimeField as ISO 8601 with timezone; Date constructor
  // parses that natively.
  return new Date(iso);
}
