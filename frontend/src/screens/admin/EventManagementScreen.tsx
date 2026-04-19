// All-events grid for admins + creators. Sort + search + filter are client-
// side because the backend's list endpoint doesn't accept a `search` or
// `sort` query param — it's a flat fetch and the Flutter app works the
// same way.

import { useMemo, useState } from 'react';
import { format } from 'date-fns';
import { Link } from 'react-router-dom';
import { useEvents } from '@/api/events';
import type { Event } from '@/models/event';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { cn } from '@/utils/cn';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

type Bucket = 'upcoming' | 'past' | 'drafts' | 'cancelled';
type Sort = 'date' | 'title' | 'type';

const BUCKETS: { value: Bucket; label: string }[] = [
  { value: 'upcoming', label: 'upcoming' },
  { value: 'past', label: 'past' },
  { value: 'drafts', label: 'drafts' },
  { value: 'cancelled', label: 'cancelled' },
];

function bucketFilter(event: Event, bucket: Bucket): boolean {
  switch (bucket) {
    case 'upcoming':
      return event.status === 'active' && !event.isPast;
    case 'past':
      return event.status === 'active' && event.isPast;
    case 'drafts':
      return event.status === 'draft';
    case 'cancelled':
      return event.status === 'cancelled';
  }
}

function sortEvents(events: readonly Event[], sort: Sort): Event[] {
  const copy = [...events];
  switch (sort) {
    case 'date':
      copy.sort((a, b) => (a.startDatetime?.getTime() ?? 0) - (b.startDatetime?.getTime() ?? 0));
      return copy;
    case 'title':
      copy.sort((a, b) => a.title.localeCompare(b.title));
      return copy;
    case 'type':
      copy.sort((a, b) => a.eventType.localeCompare(b.eventType) || a.title.localeCompare(b.title));
      return copy;
  }
}

export default function EventManagementScreen() {
  const { data = [], isPending, isError } = useEvents();
  const [bucket, setBucket] = useState<Bucket>('upcoming');
  const [sort, setSort] = useState<Sort>('date');
  const [search, setSearch] = useState('');

  const visible = useMemo(() => {
    const matching = data.filter((e) => bucketFilter(e, bucket));
    const searched = search.trim()
      ? matching.filter((e) => e.title.toLowerCase().includes(search.trim().toLowerCase()))
      : matching;
    return sortEvents(searched, sort);
  }, [data, bucket, sort, search]);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load events — try refreshing" />;

  return (
    <ContentContainer>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-medium tracking-tight">manage events</h1>
        <Link
          to="/events/add"
          className="inline-flex h-10 items-center rounded-md bg-brand-600 px-4 text-sm font-medium text-brand-on hover:bg-brand-700"
        >
          new event
        </Link>
      </header>

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="min-w-[180px] flex-1">
          <TextField
            label="search"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
            }}
            placeholder="title contains…"
          />
        </div>
        <div className="w-36">
          <Select
            label="sort"
            value={sort}
            onChange={(e) => {
              setSort(e.target.value as Sort);
            }}
            options={[
              { value: 'date', label: 'date' },
              { value: 'title', label: 'title' },
              { value: 'type', label: 'type' },
            ]}
          />
        </div>
      </div>

      <div role="tablist" aria-label="event bucket" className="mb-4 flex flex-wrap gap-1">
        {BUCKETS.map((b) => {
          const active = bucket === b.value;
          const count = data.filter((e) => bucketFilter(e, b.value)).length;
          return (
            <button
              key={b.value}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => {
                setBucket(b.value);
              }}
              className={cn(
                'rounded-full px-3 py-1 text-xs transition-colors',
                active
                  ? 'bg-brand-600 text-brand-on'
                  : 'bg-surface-dim text-foreground-secondary hover:bg-surface-raised',
              )}
            >
              {b.label} ({String(count)})
            </button>
          );
        })}
      </div>

      {visible.length === 0 ? (
        <p className="text-sm text-muted">nothing in this bucket</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {visible.map((e) => (
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
      className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface p-3 hover:bg-background"
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-foreground">{event.title}</p>
        <p className="truncate text-xs text-muted">
          {event.datetimeTbd || !event.startDatetime ? 'tbd' : format(event.startDatetime, 'EEE MMM d, h:mm a').toLowerCase()}
          {event.location ? ` · ${event.location}` : ''}
        </p>
      </div>
      <div className="flex items-center gap-2 text-xs">
        {event.eventType === 'official' ? (
          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-blue-900">official</span>
        ) : null}
        <span className="text-muted">{String(event.attendingCount)} going</span>
        <Button
          variant="ghost"
          onClick={(e) => {
            e.preventDefault();
            window.location.href = `/events/${event.id}/edit`;
          }}
        >
          edit
        </Button>
      </div>
    </Link>
  );
}
