import { format, parseISO } from 'date-fns';

export function formatSubmittedAt(iso: string, anonymous: boolean): string {
  // Anonymous surveys get a server-local date only; its yyyy-mm-dd prefix is that day.
  if (anonymous) return format(parseISO(iso.slice(0, 10)), 'MMM d, yyyy').toLowerCase();
  return format(new Date(iso), 'MMM d, yyyy h:mm a').toLowerCase();
}

export function submitterLabel(userName: string | null, anonymous: boolean): string {
  return userName ?? (anonymous ? 'anonymous' : '—');
}
