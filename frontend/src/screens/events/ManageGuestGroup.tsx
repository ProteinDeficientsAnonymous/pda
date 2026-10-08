import type { ReactNode } from 'react';

import { RsvpStatusPicker } from '@/components/ui/RsvpStatusPicker';
import type { EventGuest, RsvpInputStatus } from '@/models/event';
import { isRsvpInputStatus } from '@/models/event';
import { cn } from '@/utils/cn';

export function GuestGroup({
  label,
  guests,
  onChangeStatus,
  onRemove,
  onTogglePaid,
  onReorder,
  isPending,
}: {
  label: string;
  guests: EventGuest[];
  onChangeStatus: (userId: string, status: RsvpInputStatus, hasPlusOne: boolean) => void;
  onRemove: (userId: string) => void;
  onTogglePaid?: ((userId: string, paidConfirmed: boolean) => void) | undefined;
  onReorder?: ((userIds: string[]) => void) | undefined;
  isPending: boolean;
}) {
  const ids = guests.map((g) => g.userId);
  const move = (index: number, delta: -1 | 1) => {
    const next = [...ids];
    const [moved] = next.splice(index, 1);
    if (moved === undefined) return;
    next.splice(index + delta, 0, moved);
    onReorder?.(next);
  };

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-muted text-xs font-medium">
        {label} ({guests.length})
      </h2>
      <ul className="flex flex-col gap-2">
        {guests.map((g, i) => (
          <GuestRow
            key={g.userId}
            guest={g}
            onChangeStatus={onChangeStatus}
            onRemove={onRemove}
            onTogglePaid={onTogglePaid}
            isPending={isPending}
            orderControls={
              onReorder ? (
                <WaitlistOrderControls
                  name={g.name}
                  position={i + 1}
                  count={guests.length}
                  disabled={isPending}
                  onMove={(delta) => {
                    move(i, delta);
                  }}
                />
              ) : null
            }
          />
        ))}
      </ul>
    </div>
  );
}

function WaitlistOrderControls({
  name,
  position,
  count,
  disabled,
  onMove,
}: {
  name: string;
  position: number;
  count: number;
  disabled: boolean;
  onMove: (delta: -1 | 1) => void;
}) {
  const arrowClass =
    'bg-surface-dim text-foreground-secondary hover:bg-surface-dim/70 rounded-full px-2 py-0.5 text-xs disabled:opacity-40';
  return (
    <div className="flex items-center gap-1">
      <span className="text-muted min-w-[3ch] text-xs tabular-nums">#{position}</span>
      <button
        type="button"
        aria-label={`move ${name} up the waitlist`}
        disabled={disabled || position === 1}
        onClick={() => {
          onMove(-1);
        }}
        className={arrowClass}
      >
        ↑
      </button>
      <button
        type="button"
        aria-label={`move ${name} down the waitlist`}
        disabled={disabled || position === count}
        onClick={() => {
          onMove(1);
        }}
        className={arrowClass}
      >
        ↓
      </button>
    </div>
  );
}

function PaidBadge({
  paidConfirmed,
  onToggle,
  isPending,
}: {
  paidConfirmed: boolean;
  onToggle?: () => void;
  isPending: boolean;
}) {
  const label = paidConfirmed ? 'paid' : 'unpaid';
  const classes = paidConfirmed
    ? 'bg-info/15 text-info'
    : 'bg-surface-dim text-foreground-secondary';

  if (!onToggle) {
    return (
      <span
        className={cn('inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs', classes)}
      >
        {paidConfirmed ? '✓' : '○'} {label}
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={isPending}
      aria-pressed={paidConfirmed}
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-60',
        classes,
      )}
    >
      {paidConfirmed ? '✓' : '○'} {label}
    </button>
  );
}

function GuestRow({
  guest,
  onChangeStatus,
  onRemove,
  onTogglePaid,
  isPending,
  orderControls,
}: {
  guest: EventGuest;
  onChangeStatus: (userId: string, status: RsvpInputStatus, hasPlusOne: boolean) => void;
  onRemove: (userId: string) => void;
  onTogglePaid?: ((userId: string, paidConfirmed: boolean) => void) | undefined;
  isPending: boolean;
  orderControls: ReactNode;
}) {
  const currentStatus = isRsvpInputStatus(guest.status) ? guest.status : null;

  if (!guest.isMember) {
    return (
      <li className="border-border flex items-center justify-between gap-2 rounded-md border p-2 opacity-60">
        <span className="text-foreground text-sm">{guest.name} (not a member)</span>
        <div className="flex items-center gap-2">
          {onTogglePaid ? (
            <PaidBadge
              paidConfirmed={guest.paidConfirmed}
              isPending={isPending}
              onToggle={() => {
                onTogglePaid(guest.userId, !guest.paidConfirmed);
              }}
            />
          ) : null}
          {orderControls}
        </div>
      </li>
    );
  }

  return (
    <li className="border-border flex flex-col gap-2 rounded-md border p-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-foreground text-sm">{guest.name}</span>
          {onTogglePaid ? (
            <PaidBadge
              paidConfirmed={guest.paidConfirmed}
              isPending={isPending}
              onToggle={() => {
                onTogglePaid(guest.userId, !guest.paidConfirmed);
              }}
            />
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {orderControls}
          <button
            type="button"
            aria-label={`remove ${guest.name}`}
            onClick={() => {
              onRemove(guest.userId);
            }}
            disabled={isPending}
            className="text-muted hover:text-destructive text-xs disabled:opacity-60"
          >
            remove
          </button>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <RsvpStatusPicker
          value={currentStatus}
          disabled={isPending}
          onSelect={(status) => {
            onChangeStatus(guest.userId, status, guest.hasPlusOne);
          }}
        />
        <button
          type="button"
          aria-label={guest.hasPlusOne ? `remove ${guest.name}'s +1` : 'add +1'}
          onClick={() => {
            if (!currentStatus) return;
            onChangeStatus(guest.userId, currentStatus, !guest.hasPlusOne);
          }}
          disabled={isPending || !currentStatus}
          className="bg-surface-dim text-foreground-secondary hover:bg-surface-dim/70 rounded-full px-3 py-1 text-xs disabled:opacity-60"
        >
          {guest.hasPlusOne ? '−1' : '+1'}
        </button>
      </div>
    </li>
  );
}
