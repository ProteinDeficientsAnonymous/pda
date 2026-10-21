import { useMemo, useState } from 'react';

import { useEvents } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import type { Event } from '@/models/event';
import { EventStatus, isHosting, RsvpStatus } from '@/models/event';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { EventRow } from './EventRow';

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
