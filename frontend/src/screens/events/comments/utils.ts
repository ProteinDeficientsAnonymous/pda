import { formatDistanceToNow } from 'date-fns';

export function formatRelative(iso: string): string {
  return formatDistanceToNow(new Date(iso), { addSuffix: true }).toLowerCase();
}
