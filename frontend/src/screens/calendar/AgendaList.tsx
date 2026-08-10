import { format, isSameDay } from 'date-fns';
import { useMemo, useState } from 'react';

import { SegmentedControl } from '@/components/ui/SegmentedControl';
import {
  DEFAULT_EVENT_DURATION_MS,
  type Event as PdaEvent,
  eventClass,
  EventType,
} from '@/models/event';
import { EventBadge } from '@/screens/events/EventBadge';
import { EventCardBadges } from '@/screens/events/EventCardBadges';
import { cn } from '@/utils/cn';

type TypeFilter =
  | 'all'
  | typeof EventType.Official
  | typeof EventType.Club
  | typeof EventType.Community;

const FILTER_OPTIONS: { value: TypeFilter; label: string }[] = [
  { value: 'all', label: 'all' },
  { value: EventType.Official, label: 'pda official' },
  { value: EventType.Club, label: 'pda club' },
  { value: EventType.Community, label: 'community' },
];

interface Props {
  events: PdaEvent[];
  onSelectEvent: (event: PdaEvent) => void;
}

const lower = (d: Date, f: string) => format(d, f).toLowerCase();

function buildWhenLabel(event: PdaEvent): string {
  const start = event.startDatetime;
  if (!start || event.datetimeTbd) return event.hasPoll ? 'vote for a date' : 'date tbd';
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
  return events
    .filter((e) => {
      if (!e.startDatetime) return false;
      const end = e.endDatetime ?? new Date(e.startDatetime.getTime() + DEFAULT_EVENT_DURATION_MS);
      return end >= now;
    })
    .sort((a, b) => (a.startDatetime?.getTime() ?? 0) - (b.startDatetime?.getTime() ?? 0));
}

function tbdEvents(events: PdaEvent[]): PdaEvent[] {
  return events.filter((e) => !e.startDatetime || e.datetimeTbd);
}

function byType(events: PdaEvent[], typeFilter: TypeFilter): PdaEvent[] {
  return typeFilter === 'all' ? events : events.filter((e) => e.eventType === typeFilter);
}

export function AgendaList({ events, onSelectEvent }: Props) {
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const upcoming = useMemo(() => upcomingEvents(events), [events]);
  const filtered = useMemo(() => byType(upcoming, typeFilter), [upcoming, typeFilter]);

  const tbd = useMemo(() => tbdEvents(events), [events]);
  const pollTbd = useMemo(
    () =>
      byType(
        tbd.filter((e) => e.hasPoll),
        typeFilter,
      ),
    [tbd, typeFilter],
  );
  const plainTbd = useMemo(
    () =>
      byType(
        tbd.filter((e) => !e.hasPoll),
        typeFilter,
      ),
    [tbd, typeFilter],
  );

  const isEmpty = filtered.length === 0 && pollTbd.length === 0 && plainTbd.length === 0;

  return (
    <div className="flex flex-col">
      <div className="flex justify-center px-3 pt-3">
        <SegmentedControl<TypeFilter>
          name="agenda-type-filter"
          ariaLabel="event type filter"
          options={FILTER_OPTIONS}
          value={typeFilter}
          onChange={setTypeFilter}
        />
      </div>
      {isEmpty ? (
        <EmptyState filter={typeFilter} />
      ) : (
        <div className="flex flex-col gap-2.5 p-3">
          <TbdSection title="needs a vote" events={pollTbd} onSelect={onSelectEvent} />
          <ul className="flex flex-col gap-2.5">
            {filtered.map((event) => (
              <li key={event.id}>
                <AgendaCard event={event} onSelect={onSelectEvent} />
              </li>
            ))}
          </ul>
          <TbdSection title="date tbd" events={plainTbd} onSelect={onSelectEvent} />
        </div>
      )}
    </div>
  );
}

function TbdSection({
  title,
  events,
  onSelect,
}: {
  title: string;
  events: PdaEvent[];
  onSelect: (event: PdaEvent) => void;
}) {
  if (events.length === 0) return null;
  return (
    <div className="flex flex-col gap-2.5">
      <h2 className="text-foreground-tertiary px-0.5 text-xs font-medium uppercase">{title}</h2>
      <ul className="flex flex-col gap-2.5">
        {events.map((event) => (
          <li key={event.id}>
            <AgendaCard event={event} onSelect={onSelect} />
          </li>
        ))}
      </ul>
    </div>
  );
}

function emptyMessage(filter: TypeFilter): string {
  if (filter === EventType.Official) return 'no pda official events coming up';
  if (filter === EventType.Club) return 'no pda club events coming up';
  if (filter === EventType.Community) return 'no community events coming up';
  return 'nothing on the horizon — pop back later';
}

function EmptyState({ filter }: { filter: TypeFilter }) {
  const message = emptyMessage(filter);
  return (
    <div className="text-muted flex min-h-[40vh] flex-col items-center justify-center">
      <span aria-hidden="true" className="mb-3 text-4xl">
        🌿
      </span>
      <p className="text-sm">{message}</p>
    </div>
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
      {event.eventType === EventType.Official ||
      event.eventType === EventType.Club ||
      (event.hasPoll && event.datetimeTbd) ? (
        <div className="mt-1 flex flex-wrap gap-1.5">
          <EventBadge event={event} onCard />
          {event.hasPoll && event.datetimeTbd ? (
            <span className="rounded-full bg-black/10 px-2 py-0.5 text-xs dark:bg-white/15">
              poll open
            </span>
          ) : null}
        </div>
      ) : null}
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
      <EventCardBadges event={event} variant="card" className="mt-1.5" />
    </button>
  );
}
