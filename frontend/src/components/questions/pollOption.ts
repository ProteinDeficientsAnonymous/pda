import { isValid, parseISO } from 'date-fns';

import { EVENT_TZ_LABEL, formatEventTime } from '@/utils/datetime';

export const POLL_AVAILABILITIES = ['yes', 'maybe', 'no'] as const;
export type PollAvailability = (typeof POLL_AVAILABILITIES)[number];

export function formatPollOption(value: string): string {
  // parseISO accepts bare years like "2024", so require a time part before treating it as a datetime.
  if (!/^\d{4}-\d{2}-\d{2}T/.test(value)) return value;
  const d = parseISO(value);
  return isValid(d) ? `${formatEventTime(d, 'MMM d, yyyy h:mm a')} ${EVENT_TZ_LABEL}` : value;
}
