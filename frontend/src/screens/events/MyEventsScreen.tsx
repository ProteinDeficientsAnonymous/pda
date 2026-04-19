// Member-facing "my events" list — events the current user created or
// co-hosts. Backed by the same flat `useEvents()` feed as the calendar; the
// filter is client-side (matches the Flutter behavior where
// event_management_screen.dart had a `myEventsOnly` toggle that filtered on
// createdById == user.id || coHostIds.contains(user.id)).

import { useMemo, useState } from 'react';
import { format } from 'date-fns';
import { Link } from 'react-router-dom';
import { useEvents } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import { EventStatus, EventType } from '@/models/event';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

type Filter = 'upcoming' | 'past' | 'cancelled';

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'upcoming', label: 'upcoming' },
  { value: 'past', label: 'past' },
  { value: 'cancelled', label: 'cancelled' },
];

export default function MyEventsScreen() {
  const { data = [], isPending, isError } = useEvents();
  const userId = useAuthStore((s) => s.user?.id ?? null);
  const [filter, setFilter] = useState<Filter>('upcoming');

  const mine = useMemo(() => {
    if (!userId) return [];
    const filtered = data.filter(
      (e) => e.createdById === userId || e.coHostIds.includes(userId),
    );
    if (filter === 'cancelled') {
      return filtered
        .filter((e) => e.status === EventStatus.Cancelled)
        .sort(
          (a, b) => (b.startDatetime?.getTime() ?? 0) - (a.startDatetime?.getTime() ?? 0),
        );
    }
    const nonCancelled = filtered.filter((e) => e.status !== EventStatus.Cancelled);
    if (filter === 'upcoming') {
      return nonCancelled
        .filter((e) => !e.isPast)
        .sort(
          (a, b) => (a.startDatetime?.getTime() ?? 0) - (b.startDatetime?.getTime() ?? 0),
        );
    }
    return nonCancelled
      .filter((e) => e.isPast)
      .sort(
        (a, b) => (b.startDatetime?.getTime() ?? 0) - (a.startDatetime?.getTime() ?? 0),
      );
  }, [data, userId, filter]);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load events — try refreshing" />;

  return (
    <ContentContainer>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-medium tracking-tight">my events</h1>
        <Link
          to="/events/add"
          className="inline-flex h-10 items-center rounded-md bg-brand-600 px-4 text-sm font-medium text-brand-on hover:bg-brand-700"
        >
          create event
        </Link>
      </header>

      <div className="mb-4 flex justify-center">
        <SegmentedControl
          name="my-events-filter"
          ariaLabel="filter"
          options={FILTERS}
          value={filter}
          onChange={setFilter}
        />
      </div>

      {mine.length === 0 ? (
        <p className="text-sm text-neutral-500">
          nothing here 🌿 — events you create or co-host will show up here
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {mine.map((e) => (
            <li key={e.id}>
              <EventRow event={e} />
            </li>
          ))}
        </ul>
      )}
    </ContentContainer>
  );
}

function EventRow({ event }: { event: Event }) {
  return (
    <Link
      to={`/events/${event.id}`}
      className="flex items-center justify-between gap-3 rounded-lg border border-neutral-200 bg-white p-3 hover:bg-neutral-50"
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-neutral-800">{event.title}</p>
        <p className="truncate text-xs text-neutral-500">
          {event.datetimeTbd || !event.startDatetime
            ? 'tbd'
            : format(event.startDatetime, 'EEE MMM d, h:mm a').toLowerCase()}
          {event.location ? ` · ${event.location}` : ''}
        </p>
      </div>
      <div className="flex items-center gap-2 text-xs">
        {event.status === EventStatus.Cancelled ? (
          <span className="rounded-full bg-neutral-200 px-2 py-0.5 text-neutral-700">
            cancelled
          </span>
        ) : null}
        {event.eventType === EventType.Official ? (
          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-blue-900">official</span>
        ) : null}
        <span className="text-neutral-500">{String(event.attendingCount)} going</span>
      </div>
    </Link>
  );
}
