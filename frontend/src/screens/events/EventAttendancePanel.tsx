import { useState } from 'react';
import { toast } from 'sonner';

import { useEventStats, useSetAttendance } from '@/api/eventStats';
import type { Event, EventCancellation, EventStats } from '@/models/event';
import { rsvpGroupLabel } from '@/models/event';

import { EventCheckInList } from './EventCheckInList';

interface Props {
  event: Event;
}

const CHECK_IN_OPENS_MS_BEFORE_START = 60 * 60 * 1000;

function isCheckInOpen(event: Event): boolean {
  if (event.isPast) return true;
  if (!event.startDatetime) return false;
  return event.startDatetime.getTime() - Date.now() <= CHECK_IN_OPENS_MS_BEFORE_START;
}

export function EventAttendancePanel({ event }: Props) {
  const stats = useEventStats(event.id, true);
  const setAttendance = useSetAttendance(event.id);

  const checkInOpen = isCheckInOpen(event);

  if (stats.isLoading) {
    return <p className="text-muted text-sm">loading stats…</p>;
  }
  if (stats.isError || !stats.data) {
    return <p className="text-sm text-red-600">couldn't load stats — try refreshing</p>;
  }
  return (
    <div className="flex flex-col gap-4">
      <StatsRow stats={stats.data} />
      {checkInOpen ? (
        <EventCheckInList
          guests={event.guests}
          onMark={(userId, attendance, forPlusOne) => {
            setAttendance.mutate(
              { userId, attendance, forPlusOne: forPlusOne ?? false },
              { onError: () => toast.error("couldn't save check-in — try again") },
            );
          }}
          isPending={setAttendance.isPending}
        />
      ) : (
        <p className="text-muted text-xs">check-in opens an hour before the event</p>
      )}
      <CancellationsList cancellations={stats.data.cancellations} />
    </div>
  );
}

function StatsRow({ stats }: { stats: EventStats }) {
  return (
    <div className="flex flex-wrap gap-2 text-xs">
      <Chip label="going" value={stats.goingCount} />
      <Chip label="maybe" value={stats.maybeCount} />
      <Chip label="can't go" value={stats.cantGoCount} />
      <Chip label="no response" value={stats.noResponseCount} />
      {stats.waitlistedCount > 0 ? <Chip label="waitlisted" value={stats.waitlistedCount} /> : null}
    </div>
  );
}

function Chip({ label, value }: { label: string; value: number }) {
  return (
    <span className="bg-surface-dim text-foreground-secondary rounded-full px-3 py-1">
      <span className="text-foreground font-medium">{value}</span> {label}
    </span>
  );
}

function CancellationsList({ cancellations }: { cancellations: EventCancellation[] }) {
  const [withinDays, setWithinDays] = useState<number | null>(null);

  if (cancellations.length === 0) return null;

  const filtered =
    withinDays === null
      ? cancellations
      : cancellations.filter((c) => c.daysBeforeEvent <= withinDays);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-muted text-xs font-medium">cancellations</h3>
        <WithinDaysFilter value={withinDays} onChange={setWithinDays} />
      </div>
      {filtered.length === 0 ? (
        <p className="text-muted text-xs">no cancellations within {String(withinDays)} days</p>
      ) : (
        <ul className="flex flex-col gap-1 text-sm">
          {filtered.map((c) => (
            <li key={c.userId} className="text-foreground-secondary">
              <span className="text-foreground">{c.name}</span> —{' '}
              {formatLeadTime(c.daysBeforeEvent, c.sameDay)}
              {c.previousStatus ? ` (was ${rsvpGroupLabel(c.previousStatus)})` : ''}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function WithinDaysFilter({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (v: number | null) => void;
}) {
  const current = value ?? 0;
  const decrement = () => {
    if (value === null || value <= 1) onChange(null);
    else onChange(value - 1);
  };
  const increment = () => {
    onChange(current + 1);
  };

  return (
    <div className="text-muted flex items-center gap-1 text-xs">
      <span>within</span>
      <div className="border-border bg-surface flex items-center overflow-hidden rounded-full border">
        <button
          type="button"
          onClick={decrement}
          disabled={value === null}
          aria-label="fewer days"
          className="text-foreground-secondary hover:bg-surface-dim px-2 py-0.5 leading-none disabled:opacity-40"
        >
          −
        </button>
        <span className="text-foreground min-w-[2ch] text-center text-xs tabular-nums">
          {value ?? 'all'}
        </span>
        <button
          type="button"
          onClick={increment}
          aria-label="more days"
          className="text-foreground-secondary hover:bg-surface-dim px-2 py-0.5 leading-none"
        >
          +
        </button>
      </div>
      <span>days</span>
    </div>
  );
}

function formatLeadTime(days: number, sameDay: boolean): string {
  if (days < 0) return `cancelled ${String(Math.abs(days))} days after start`;
  if (sameDay) return 'cancelled same day';
  if (days === 1) return 'cancelled 1 day before';
  return `cancelled ${String(days)} days before`;
}
