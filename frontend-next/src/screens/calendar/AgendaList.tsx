// Custom agenda (list) view — a flat list of event cards, each colored by
// event type. No rbc date/time columns; title sits on top, date + time line
// sits underneath. Mirrors the "cleaner" list layout the user asked for.

import { format, isSameDay } from 'date-fns';
import { eventClass, type Event as PdaEvent } from '@/models/event';
import { cn } from '@/utils/cn';

interface Props {
  events: PdaEvent[];
  onSelectEvent: (event: PdaEvent) => void;
}

const lower = (d: Date, f: string) => format(d, f).toLowerCase();

function buildWhenLabel(event: PdaEvent): string {
  const start = event.startDatetime;
  if (!start) return '';
  const startDate = lower(start, 'EEE, MMM d');
  const startTime = lower(start, 'h:mmaaa');
  const end = event.endDatetime;
  if (!end) return `${startDate} · ${startTime}`;
  if (isSameDay(start, end)) return `${startDate} · ${startTime}`;
  const endDate = lower(end, 'EEE, MMM d');
  return `${startDate} – ${endDate}`;
}

function upcomingEvents(events: PdaEvent[]): PdaEvent[] {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return events
    .filter((e) => {
      if (!e.startDatetime) return false;
      const end = e.endDatetime ?? e.startDatetime;
      return end >= now;
    })
    .sort((a, b) => (a.startDatetime?.getTime() ?? 0) - (b.startDatetime?.getTime() ?? 0));
}

export function AgendaList({ events, onSelectEvent }: Props) {
  const upcoming = upcomingEvents(events);

  if (upcoming.length === 0) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center text-neutral-500">
        <span aria-hidden="true" className="mb-3 text-4xl">
          🌿
        </span>
        <p className="text-sm">nothing on the horizon — pop back later</p>
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-2.5 p-3">
      {upcoming.map((event) => (
        <li key={event.id}>
          <AgendaCard event={event} onSelect={onSelectEvent} />
        </li>
      ))}
    </ul>
  );
}

interface CardProps {
  event: PdaEvent;
  onSelect: (event: PdaEvent) => void;
}

function AgendaCard({ event, onSelect }: CardProps) {
  const when = buildWhenLabel(event);
  return (
    <button
      type="button"
      onClick={() => {
        onSelect(event);
      }}
      aria-label={event.title}
      className={cn(
        eventClass(event),
        'block w-full rounded-lg px-3.5 py-3 text-left shadow-sm transition hover:shadow-md',
      )}
    >
      <div className="text-[15px] font-semibold">{event.title}</div>
      {when ? <div className="mt-1 text-[13px] opacity-90">{when}</div> : null}
      {event.location ? (
        <div className="mt-0.5 flex items-center gap-1 text-xs opacity-90">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-3 w-3 shrink-0"
            aria-hidden="true"
          >
            <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0116 0z" />
            <circle cx="12" cy="10" r="3" />
          </svg>
          <span className="truncate">{event.location}</span>
        </div>
      ) : null}
    </button>
  );
}
