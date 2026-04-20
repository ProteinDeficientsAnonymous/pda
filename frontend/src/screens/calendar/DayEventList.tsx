// Custom day view — stacked list of event cards instead of rbc's hour-by-hour
// time grid. Mirrors `frontend/lib/screens/calendar/day_view.dart` —
// cards show title, time range, location (with pin icon), and a 2-line
// description preview. Empty state reads "nothing today 🌿".

import { format, isSameDay } from 'date-fns';
import { eventClass, type Event as PdaEvent } from '@/models/event';
import { cn } from '@/utils/cn';

interface Props {
  date: Date;
  events: PdaEvent[];
  onSelectEvent: (event: PdaEvent) => void;
}

const lower = (d: Date, f: string) => format(d, f).toLowerCase();

function buildTimeRange(event: PdaEvent): string {
  const start = event.startDatetime;
  if (!start) return '';
  const startTime = lower(start, 'h:mmaaa');
  const end = event.endDatetime;
  if (!end) return startTime;
  const endTime = lower(end, 'h:mmaaa');
  if (isSameDay(start, end)) return `${startTime} – ${endTime}`;
  return `${lower(start, 'MMM d')} ${startTime} – ${lower(end, 'MMM d')} ${endTime}`;
}

function eventsForDay(events: PdaEvent[], day: Date): PdaEvent[] {
  const dayStart = new Date(day);
  dayStart.setHours(0, 0, 0, 0);
  const dayEnd = new Date(dayStart);
  dayEnd.setDate(dayEnd.getDate() + 1);
  return events
    .filter((e) => {
      if (!e.startDatetime) return false;
      const end = e.endDatetime ?? new Date(e.startDatetime.getTime() + 60 * 1000);
      return e.startDatetime < dayEnd && end > dayStart;
    })
    .sort((a, b) => (a.startDatetime?.getTime() ?? 0) - (b.startDatetime?.getTime() ?? 0));
}

export function DayEventList({ date, events, onSelectEvent }: Props) {
  const dayEvents = eventsForDay(events, date);

  if (dayEvents.length === 0) {
    return (
      <div className="text-muted flex min-h-[40vh] flex-col items-center justify-center">
        <span aria-hidden="true" className="mb-3 text-4xl">
          🌿
        </span>
        <p className="text-sm">nothing today</p>
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-2.5 p-3">
      {dayEvents.map((event) => (
        <li key={event.id}>
          <DayEventCard event={event} onSelect={onSelectEvent} />
        </li>
      ))}
    </ul>
  );
}

interface CardProps {
  event: PdaEvent;
  onSelect: (event: PdaEvent) => void;
}

function DayEventCard({ event, onSelect }: CardProps) {
  const timeRange = buildTimeRange(event);
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
      {timeRange ? <div className="mt-1 text-[13px] opacity-90">{timeRange}</div> : null}
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
      {event.description ? (
        <p className="mt-1 line-clamp-2 text-xs opacity-90">{event.description}</p>
      ) : null}
    </button>
  );
}
