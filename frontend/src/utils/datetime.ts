import { tz, TZDate } from '@date-fns/tz';
import { format, isSameDay, startOfDay } from 'date-fns';

import type { Birthday, Veganniversary } from '@/models/user';

// Events happen in nyc, so show their times there no matter where the viewer is (#2679).
export const COMMUNITY_TZ_NAME = 'America/New_York';
const COMMUNITY_TZ = tz(COMMUNITY_TZ_NAME);
export const EVENT_TZ_LABEL = 'et';

export function formatEventTime(date: Date, pattern: string): string {
  return format(date, pattern, { in: COMMUNITY_TZ }).toLowerCase();
}

export function toEventZone(date: Date): TZDate {
  return new TZDate(date.getTime(), COMMUNITY_TZ_NAME);
}

export function startOfEventDay(date: Date): Date {
  return startOfDay(date, { in: COMMUNITY_TZ });
}

export function parseEventDay(raw: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw);
  if (!m) return null;
  const day = new TZDate(Number(m[1]), Number(m[2]) - 1, Number(m[3]), COMMUNITY_TZ_NAME);
  return isNaN(day.getTime()) ? null : day;
}

// react-big-calendar only lays out in the browser zone, so hand it et wall-clock times.
export function toEventWallClock(date: Date): Date {
  const et = toEventZone(date);
  return new Date(
    et.getFullYear(),
    et.getMonth(),
    et.getDate(),
    et.getHours(),
    et.getMinutes(),
    et.getSeconds(),
  );
}

export function isSameEventDay(a: Date, b: Date): boolean {
  return isSameDay(a, b, { in: COMMUNITY_TZ });
}

export function formatEventDateTime(
  start: Date | null,
  end: Date | null,
  datetimeTbd = false,
): string {
  if (datetimeTbd || !start) return 'date & time tbd';
  const startStr = formatEventTime(start, 'EEE MMM d, h:mm a');
  if (!end) return `${startStr} ${EVENT_TZ_LABEL}`;
  if (isSameEventDay(start, end)) {
    return `${startStr} – ${formatEventTime(end, 'h:mm a')} ${EVENT_TZ_LABEL}`;
  }
  return `${startStr} → ${formatEventTime(end, 'EEE MMM d, h:mm a')} ${EVENT_TZ_LABEL}`;
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

export function formatVeganniversary(v: Veganniversary): string {
  if (v.day) return formatBirthday({ month: v.month, day: v.day, year: v.year });
  const month = format(new Date(2000, v.month - 1, 1), 'MMMM').toLowerCase();
  return `${month} ${String(v.year)}`;
}

export const MONTH_OPTIONS = [
  'january',
  'february',
  'march',
  'april',
  'may',
  'june',
  'july',
  'august',
  'september',
  'october',
  'november',
  'december',
].map((name, i) => ({ value: String(i + 1), label: name }));
