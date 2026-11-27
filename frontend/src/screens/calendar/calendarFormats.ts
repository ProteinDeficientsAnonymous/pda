import { format } from 'date-fns';

import { EVENT_TZ_LABEL } from '@/utils/datetime';

// react-big-calendar passes et wall-clock dates (see toEventWallClock), so format them as-is.
const lower = (d: Date, f: string) => format(d, f).toLowerCase();

export function formatAgendaTime(d: Date): string {
  return `${lower(d, 'h:mmaaa')} ${EVENT_TZ_LABEL}`;
}

export function formatEventTimeRange({ start, end }: { start: Date; end: Date }): string {
  return `${lower(start, 'h:mmaaa')} – ${lower(end, 'h:mmaaa')} ${EVENT_TZ_LABEL}`;
}
