import { format } from 'date-fns';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { useEvents } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import type { Event } from '@/models/event';
import { EventStatus, EventType, RsvpStatus } from '@/models/event';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { EventCardBadges } from './EventCardBadges';

type Filter = 'upcoming' | 'past' | 'drafts' | 'cancelled';

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'upcoming', label: 'upcoming' },
  { value: 'past', label: 'past' },
  { value: 'drafts', label: 'drafts' },
  { value: 'cancelled', label: 'cancelled' },
];

const EMPTY_COPY: Record<Filter, string> = {
  upcoming: "nothing coming up 🌿 — events you're hosting or going to will show up here",
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
    const isHost = (e: Event) => e.createdById === userId || e.coHostIds.includes(userId);
    const mineActive = sourceData.filter(
      (e) => isHost(e) || e.myRsvp === RsvpStatus.Attending || e.myRsvp === RsvpStatus.Maybe,
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
      <div className="mb-6 flex flex-wrap items-center justify-end gap-3">
        <Link
          to="/events/add"
          className="bg-brand-600 text-brand-on hover:bg-brand-700 inline-flex h-10 items-center rounded-md px-4 text-sm font-medium"
        >
          create event
        </Link>
      </div>

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
        <p className="text-muted text-sm">{EMPTY_COPY[filter]}</p>
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
