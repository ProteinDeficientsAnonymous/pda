// Member-facing "my events" list — events the current user created or
// co-hosts. Active events come from the same flat `useEvents()` feed as the
// calendar (client-split by start time into upcoming/past). Drafts and
// cancelled events come from dedicated `?status=` queries; backend already
// scopes those to events the user created or co-hosts.

import { useMemo, useState } from 'react';
import { format } from 'date-fns';
import { Link } from 'react-router-dom';
import { useEvents } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import { EventStatus, EventType } from '@/models/event';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

type Filter = 'upcoming' | 'past' | 'drafts' | 'cancelled';

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'upcoming', label: 'upcoming' },
  { value: 'past', label: 'past' },
  { value: 'drafts', label: 'drafts' },
  { value: 'cancelled', label: 'cancelled' },
];

const EMPTY_COPY: Record<Filter, string> = {
  upcoming: 'nothing coming up 🌿 — events you create or co-host will show up here',
  past: 'no past events yet 🌿',
  drafts: 'no drafts saved 🌿 — start one and we\u2019ll keep it here until you publish',
  cancelled: 'no cancelled events 🌿',
};

type EventsQuery = ReturnType<typeof useEvents>;

function pickSourceQuery(
  filter: Filter,
  sources: { active: EventsQuery; drafts: EventsQuery; cancelled: EventsQuery },
): EventsQuery {
  if (filter === 'drafts') return sources.drafts;
  if (filter === 'cancelled') return sources.cancelled;
  return sources.active;
}

export default function MyEventsScreen() {
  const userId = useAuthStore((s) => s.user?.id ?? null);
  const [filter, setFilter] = useState<Filter>('upcoming');

  const activeQuery = useEvents();
  const draftsQuery = useEvents(EventStatus.Draft);
  const cancelledQuery = useEvents(EventStatus.Cancelled);

  const isHostOnlyTab = filter === 'drafts' || filter === 'cancelled';
  const sourceQuery = pickSourceQuery(filter, {
    active: activeQuery,
    drafts: draftsQuery,
    cancelled: cancelledQuery,
  });
  const mine = useMemo(() => {
    const sourceData = sourceQuery.data ?? [];
    if (!userId) return [];
    // Drafts/cancelled tabs: backend already scopes to host/co-host. No
    // additional filtering needed.
    if (isHostOnlyTab) {
      return [...sourceData].sort(
        (a, b) => (b.startDatetime?.getTime() ?? 0) - (a.startDatetime?.getTime() ?? 0),
      );
    }
    const mineActive = sourceData.filter(
      (e) => e.createdById === userId || e.coHostIds.includes(userId),
    );
    if (filter === 'upcoming') {
      return mineActive
        .filter((e) => !e.isPast)
        .sort((a, b) => (a.startDatetime?.getTime() ?? 0) - (b.startDatetime?.getTime() ?? 0));
    }
    return mineActive
      .filter((e) => e.isPast)
      .sort((a, b) => (b.startDatetime?.getTime() ?? 0) - (a.startDatetime?.getTime() ?? 0));
  }, [sourceQuery.data, userId, filter, isHostOnlyTab]);

  if (sourceQuery.isPending) return <ContentLoading />;
  if (sourceQuery.isError) return <ContentError message="couldn't load events — try refreshing" />;

  return (
    <ContentContainer>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-medium tracking-tight">my events</h1>
        <Link
          to="/events/add"
          className="bg-brand-600 text-brand-on hover:bg-brand-700 inline-flex h-10 items-center rounded-md px-4 text-sm font-medium"
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
        <p className="text-sm text-neutral-500">{EMPTY_COPY[filter]}</p>
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
        {event.status === EventStatus.Draft ? (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-900">draft</span>
        ) : null}
        {event.eventType === EventType.Official ? (
          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-blue-900">official</span>
        ) : null}
        <span className="text-neutral-500">{String(event.attendingCount)} going</span>
      </div>
    </Link>
  );
}
