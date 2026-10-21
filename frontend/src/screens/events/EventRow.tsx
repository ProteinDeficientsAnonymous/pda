import { format } from 'date-fns';
import { Link } from 'react-router-dom';

import type { Event } from '@/models/event';
import { eventPath, EventStatus, EventType } from '@/models/event';

import { EventCardBadges } from './EventCardBadges';

export function EventRow({ event }: { event: Event }) {
  return (
    <Link
      to={eventPath(event)}
      className="border-border bg-surface hover:bg-surface-dim flex items-center justify-between gap-3 rounded-lg border p-3 transition-colors"
    >
      <div className="min-w-0">
        <p className="text-foreground truncate text-sm font-medium">{event.title}</p>
        <p className="text-foreground-tertiary truncate text-xs">
          {event.datetimeTbd || !event.startDatetime
            ? 'tbd'
            : format(event.startDatetime, 'EEE MMM d, h:mm a').toLowerCase()}
          {event.location ? ` · ${event.location}` : ''}
        </p>
        <EventCardBadges event={event} variant="row" className="mt-1.5" />
      </div>
      <div className="flex items-center gap-2 text-xs">
        {event.status === EventStatus.Cancelled ? (
          <span className="bg-surface-dim text-foreground-secondary rounded-full px-2 py-0.5">
            cancelled
          </span>
        ) : null}
        {event.status === EventStatus.Draft ? (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-900 dark:bg-amber-900/40 dark:text-amber-200">
            draft
          </span>
        ) : null}
        {event.eventType === EventType.Official ? (
          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-blue-900 dark:bg-blue-900/40 dark:text-blue-200">
            official
          </span>
        ) : null}
      </div>
    </Link>
  );
}
