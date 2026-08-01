import { useState } from 'react';

import type { AttendanceStatusValue, EventGuest, RsvpInputStatus } from '@/models/event';
import { AttendanceStatus, RsvpStatus } from '@/models/event';
import { cn } from '@/utils/cn';

// Third-person labels — RSVP_STATUS_LABELS is worded for the member's own picker ("i'm going").
const CHECK_IN_FILTERS: { status: RsvpInputStatus; label: string }[] = [
  { status: RsvpStatus.Attending, label: 'going' },
  { status: RsvpStatus.Maybe, label: 'maybe' },
  { status: RsvpStatus.CantGo, label: "can't go" },
];

export function EventCheckInList({
  guests,
  onMark,
  isPending,
}: {
  guests: EventGuest[];
  onMark: (userId: string, attendance: AttendanceStatusValue) => void;
  isPending: boolean;
}) {
  const [statusFilter, setStatusFilter] = useState<RsvpInputStatus | null>(null);

  if (guests.length === 0) {
    return <p className="text-muted text-xs">no rsvps to check in</p>;
  }

  const filtered = statusFilter === null ? guests : guests.filter((g) => g.status === statusFilter);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-muted text-xs font-medium">check-in</h3>
        <StatusFilter value={statusFilter} onChange={setStatusFilter} />
      </div>
      {filtered.length === 0 ? (
        <p className="text-muted text-xs">nobody with that rsvp 🌿</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {filtered.map((g) => (
            <li
              key={g.userId}
              className="border-border flex items-center justify-between gap-2 rounded-md border p-2"
            >
              <span className="flex min-w-0 items-center gap-2">
                <span className="text-foreground truncate text-sm">{g.name}</span>
                <span className="text-muted shrink-0 text-xs">{guestStatusLabel(g.status)}</span>
              </span>
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
      )}
    </div>
  );
}

function guestStatusLabel(status: string): string {
  return CHECK_IN_FILTERS.find((s) => s.status === status)?.label ?? status;
}

function StatusFilter({
  value,
  onChange,
}: {
  value: RsvpInputStatus | null;
  onChange: (v: RsvpInputStatus | null) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1">
      <FilterChip
        active={value === null}
        label="all"
        onClick={() => {
          onChange(null);
        }}
      />
      {CHECK_IN_FILTERS.map((s) => (
        <FilterChip
          key={s.status}
          active={value === s.status}
          label={s.label}
          onClick={() => {
            onChange(s.status);
          }}
        />
      ))}
    </div>
  );
}

function FilterChip({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        'rounded-full px-2 py-0.5 text-xs transition-colors',
        active
          ? 'bg-brand-600 text-white'
          : 'bg-surface-dim text-foreground-secondary hover:bg-surface-dim/70',
      )}
    >
      {label}
    </button>
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
