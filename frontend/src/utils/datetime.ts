import { format, isSameDay } from 'date-fns';

import type { Birthday } from '@/models/user';

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

export function formatShortDateTime(date: Date): string {
  return format(date, 'MMM d, h:mma').toLowerCase();
}

export function parseIsoDate(iso: string): Date {
  // Backend serializes DateTimeField as ISO 8601 with timezone; Date constructor
  // parses that natively.
  return new Date(iso);
}

export function formatBirthday(birthday: Birthday): string {
  const monthDay = format(new Date(2000, birthday.month - 1, birthday.day), 'MMMM d').toLowerCase();
  return birthday.year ? `${monthDay}, ${String(birthday.year)}` : monthDay;
}
