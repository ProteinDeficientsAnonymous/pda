import { format } from 'date-fns';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { useEvents } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import type { Event } from '@/models/event';
import { EventStatus, EventType, isHosting, RsvpStatus } from '@/models/event';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { EventCardBadges } from './EventCardBadges';

type Filter = 'upcoming' | 'hosting' | 'past' | 'drafts' | 'cancelled';

const FILTER_LABELS: Record<Filter, string> = {
  upcoming: 'upcoming',
  hosting: 'hosting',
  past: 'past',
  drafts: 'drafts',
  cancelled: 'cancelled',
};

const EMPTY_COPY: Record<Filter, string> = {
  upcoming: "nothing coming up 🌿 — events you're hosting or going to will show up here",
  hosting: "nothing you're hosting right now 🌿",
  past: 'no past events yet 🌿',
  drafts: 'no drafts saved 🌿 — start one and we\u2019ll keep it here until you publish',
  cancelled: 'no cancelled events 🌿',
};

function isMine(event: Event, userId: string): boolean {
  return (
    isHosting(event, userId) ||
    event.myRsvp === RsvpStatus.Attending ||
    event.myRsvp === RsvpStatus.Maybe
  );
}

export default function MyEventsScreen() {
  const userId = useAuthStore((s) => s.user?.id ?? null);
  const [filter, setFilter] = useState<Filter>('upcoming');

  const activeQuery = useEvents();
  const draftsQuery = useEvents(EventStatus.Draft);
  const cancelledQuery = useEvents(EventStatus.Cancelled);

  const eventsByFilter = useMemo((): Record<Filter, Event[]> => {
    if (!userId) return { upcoming: [], hosting: [], past: [], drafts: [], cancelled: [] };
    const mineActive = (activeQuery.data ?? []).filter((e) => isMine(e, userId));
    const upcoming = mineActive
      .filter((e) => !e.isPast)
      .sort((a, b) => (a.startDatetime?.getTime() ?? 0) - (b.startDatetime?.getTime() ?? 0));
    return {
      upcoming,
      hosting: upcoming.filter((e) => isHosting(e, userId)),
      past: mineActive
        .filter((e) => e.isPast)
        .sort((a, b) => (b.startDatetime?.getTime() ?? 0) - (a.startDatetime?.getTime() ?? 0)),
      drafts: [...(draftsQuery.data ?? [])].sort(
        (a, b) => (b.startDatetime?.getTime() ?? 0) - (a.startDatetime?.getTime() ?? 0),
      ),
      cancelled: [...(cancelledQuery.data ?? [])].sort(
        (a, b) => (b.startDatetime?.getTime() ?? 0) - (a.startDatetime?.getTime() ?? 0),
      ),
    };
  }, [activeQuery.data, draftsQuery.data, cancelledQuery.data, userId]);

  const availableFilters = (Object.keys(FILTER_LABELS) as Filter[]).filter(
    (f) => eventsByFilter[f].length > 0,
  );
  const activeFilter = availableFilters.includes(filter) ? filter : (availableFilters[0] ?? filter);

  if (activeQuery.isPending || draftsQuery.isPending || cancelledQuery.isPending) {
    return <ContentLoading />;
  }
  if (activeQuery.isError || draftsQuery.isError || cancelledQuery.isError) {
    return <ContentError message="couldn't load events — try refreshing" />;
  }

  const mine = eventsByFilter[activeFilter];

  return (
    <ContentContainer className="pt-4 md:pt-6">
      {availableFilters.length > 1 ? (
        <div className="mb-4 flex justify-center">
          <SegmentedControl
            name="my-events-filter"
            ariaLabel="filter"
            options={availableFilters.map((f) => ({ value: f, label: FILTER_LABELS[f] }))}
            value={activeFilter}
            onChange={setFilter}
          />
        </div>
      ) : null}

      {mine.length === 0 ? (
        <p className="text-muted text-sm">{EMPTY_COPY[activeFilter]}</p>
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
