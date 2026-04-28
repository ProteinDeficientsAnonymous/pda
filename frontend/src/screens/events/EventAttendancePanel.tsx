// Host-only attendance panel rendered on a dedicated page (/events/:id/attendance).
// Gated upstream in EventAttendanceScreen — component itself expects to only
// render when the viewer is creator/co-host/admin.
//
// Sections:
//   - stats row + cancellations list: always visible.
//   - check-in controls: open 1h before start, never close.
// Cancellation lead time is inferred from `CANT_GO` rows' updated_at — lossy
// for users who flipped statuses (see docs/event-attendance-stats-plan.md).

import { useState } from 'react';
import { useSetAttendance, useEventStats } from '@/api/eventStats';
import type {
  AttendanceStatusValue,
  Event,
  EventCancellation,
  EventGuest,
  EventStats,
} from '@/models/event';
import { AttendanceStatus, RsvpServerStatus } from '@/models/event';
import { cn } from '@/utils/cn';

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

  const goingGuests = event.guests.filter((g) => g.status === RsvpServerStatus.Attending);
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
        <CheckInList
          guests={goingGuests}
          onMark={(userId, attendance) => {
            setAttendance.mutate({ userId, attendance });
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

function CheckInList({
  guests,
  onMark,
  isPending,
}: {
  guests: EventGuest[];
  onMark: (userId: string, attendance: AttendanceStatusValue) => void;
  isPending: boolean;
}) {
  if (guests.length === 0) {
    return <p className="text-muted text-xs">no going rsvps to check in</p>;
  }
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-muted text-xs font-medium">check-in</h3>
      <ul className="flex flex-col gap-2">
        {guests.map((g) => (
          <li
            key={g.userId}
            className="border-border flex items-center justify-between gap-2 rounded-md border p-2"
          >
            <span className="text-foreground text-sm">{g.name}</span>
            <div className="flex gap-1">
              <AttendanceButton
                active={g.attendance === AttendanceStatus.Attended}
                label="attended"
                onClick={() => {
                  onMark(g.userId, AttendanceStatus.Attended);
                }}
                disabled={isPending}
              />
              <AttendanceButton
                active={g.attendance === AttendanceStatus.NoShow}
                label="no-show"
                onClick={() => {
                  onMark(g.userId, AttendanceStatus.NoShow);
                }}
                disabled={isPending}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function AttendanceButton({
  active,
  label,
  onClick,
  disabled,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      className={cn(
        'rounded-full px-3 py-1 text-xs transition-colors',
        active
          ? 'bg-brand-600 text-white'
          : 'bg-surface-dim text-foreground-secondary hover:bg-surface-dim/70',
        disabled && 'opacity-60',
      )}
    >
      {label}
    </button>
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
              {formatLeadTime(c.daysBeforeEvent)}
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

function formatLeadTime(days: number): string {
  if (days < 0) return `cancelled ${String(Math.abs(days))} days after start`;
  if (days === 0) return 'cancelled same day';
  if (days === 1) return 'cancelled 1 day before';
  return `cancelled ${String(days)} days before`;
}
