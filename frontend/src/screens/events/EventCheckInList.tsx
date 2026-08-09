import { useState } from 'react';

import type { AttendanceStatusValue, EventGuest, RsvpServerStatusValue } from '@/models/event';
import { AttendanceStatus, RSVP_GROUP_LABELS, rsvpGroupLabel } from '@/models/event';
import { cn } from '@/utils/cn';

function firstName(name: string): string {
  return name.split(' ')[0] ?? name;
}

export function EventCheckInList({
  guests,
  onMark,
  isPending,
}: {
  guests: EventGuest[];
  onMark: (userId: string, attendance: AttendanceStatusValue, forPlusOne?: boolean) => void;
  isPending: boolean;
}) {
  const [statusFilter, setStatusFilter] = useState<RsvpServerStatusValue | null>(null);

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
            <li key={g.userId} className="flex flex-col gap-2">
              <div className="border-border flex items-center justify-between gap-2 rounded-md border p-2">
                <span className="flex min-w-0 items-center gap-2">
                  <span className="text-foreground truncate text-sm">{g.name}</span>
                  <span className="text-muted shrink-0 text-xs">{rsvpGroupLabel(g.status)}</span>
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
                    active={g.attendance === AttendanceStatus.DidntGo}
                    label="didn't attend"
                    onClick={() => {
                      onMark(g.userId, AttendanceStatus.DidntGo);
                    }}
                    disabled={isPending}
                  />
                </div>
              </div>
              {g.hasPlusOne ? (
                <div className="border-border bg-surface-dim/40 ml-4 flex items-center justify-between gap-2 rounded-md border p-2">
                  <span className="text-foreground-secondary truncate text-sm">
                    {firstName(g.name)}&apos;s +1
                  </span>
                  <div className="flex gap-1">
                    <AttendanceButton
                      active={g.plusOneAttendance === AttendanceStatus.Attended}
                      label="attended"
                      onClick={() => {
                        onMark(g.userId, AttendanceStatus.Attended, true);
                      }}
                      disabled={isPending}
                    />
                    <AttendanceButton
                      active={g.plusOneAttendance === AttendanceStatus.DidntGo}
                      label="didn't attend"
                      onClick={() => {
                        onMark(g.userId, AttendanceStatus.DidntGo, true);
                      }}
                      disabled={isPending}
                    />
                  </div>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StatusFilter({
  value,
  onChange,
}: {
  value: RsvpServerStatusValue | null;
  onChange: (v: RsvpServerStatusValue | null) => void;
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
      {RSVP_GROUP_LABELS.map((s) => (
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
