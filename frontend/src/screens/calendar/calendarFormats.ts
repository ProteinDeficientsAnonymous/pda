import { EVENT_TZ_LABEL, formatEventTime } from '@/utils/datetime';

export function formatAgendaTime(d: Date): string {
  return `${formatEventTime(d, 'h:mmaaa')} ${EVENT_TZ_LABEL}`;
}

export function formatEventTimeRange({ start, end }: { start: Date; end: Date }): string {
  return `${formatEventTime(start, 'h:mmaaa')} – ${formatEventTime(end, 'h:mmaaa')} ${EVENT_TZ_LABEL}`;
}
