import { format } from 'date-fns';

import type { AttendedEvent } from '@/api/attendedEvents';

export function AttendedEventsNote({
  events,
  label = 'events attended',
}: {
  events: AttendedEvent[];
  label?: string;
}) {
  if (events.length === 0) return null;
  return (
    <div className="mt-1">
      <p className="text-muted text-xs font-medium">{label}</p>
      <ul className="text-muted mt-0.5 flex flex-col gap-0.5 text-xs">
        {events.map((e) => (
          <li key={e.eventId}>
            {e.title.toLowerCase()}
            {' — '}
            {e.startDatetime ? format(e.startDatetime, 'MMM d, yyyy').toLowerCase() : 'date tbd'}
            {' · '}
            {e.eventType}
          </li>
        ))}
      </ul>
    </div>
  );
}
