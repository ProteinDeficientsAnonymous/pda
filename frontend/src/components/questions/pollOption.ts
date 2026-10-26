import { format, isValid, parseISO } from 'date-fns';

export function formatPollOption(value: string): string {
  // parseISO accepts bare years like "2024", so require a time part before treating it as a datetime.
  if (!/^\d{4}-\d{2}-\d{2}T/.test(value)) return value;
  const d = parseISO(value);
  return isValid(d) ? format(d, 'MMM d, yyyy h:mm a').toLowerCase() : value;
}
