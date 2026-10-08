import { SortableList } from '@/components/SortableList';
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
  readOnly,
}: {
  label: string;
  guests: EventGuest[];
  onChangeStatus: (userId: string, status: RsvpInputStatus, hasPlusOne: boolean) => void;
  onRemove: (userId: string) => void;
  onTogglePaid?: ((userId: string, paidConfirmed: boolean) => void) | undefined;
  onReorder?: ((userIds: string[]) => void) | undefined;
  isPending: boolean;
  readOnly: boolean;
}) {
  const row = (g: EventGuest) => (
    <GuestRow
      guest={g}
      readOnly={readOnly}
      onChangeStatus={onChangeStatus}
      onRemove={onRemove}
      onTogglePaid={onTogglePaid}
      isPending={isPending}
    />
  );

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-muted text-xs font-medium">
        {label} ({guests.length})
      </h2>
      {onReorder && !readOnly ? (
        <SortableList
          ariaLabel={`${label} order`}
          items={guests.map((g) => ({ id: g.userId, guest: g }))}
          onReorder={onReorder}
          renderItem={(item) => row(item.guest)}
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {guests.map((g) => (
            <li key={g.userId}>{row(g)}</li>
          ))}
        </ul>
      )}
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
  readOnly,
}: {
  guest: EventGuest;
  onChangeStatus: (userId: string, status: RsvpInputStatus, hasPlusOne: boolean) => void;
  onRemove: (userId: string) => void;
  onTogglePaid?: ((userId: string, paidConfirmed: boolean) => void) | undefined;
  isPending: boolean;
  readOnly: boolean;
}) {
  const currentStatus = isRsvpInputStatus(guest.status) ? guest.status : null;

  if (readOnly) {
    return (
      <div className="border-border flex items-center justify-between gap-2 rounded-md border p-2">
        <span className="text-foreground text-sm">
          {guest.name}
          {!guest.isMember ? ' (not a member)' : ''}
        </span>
        <span className="text-muted text-xs">
          {currentStatus ?? guest.status}
          {guest.hasPlusOne ? ' · +1' : ''}
        </span>
      </div>
    );
  }

  if (!guest.isMember) {
    return (
      <div className="border-border flex items-center justify-between gap-2 rounded-md border p-2 opacity-60">
        <span className="text-foreground text-sm">{guest.name} (not a member)</span>
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
    );
  }

  return (
    <div className="border-border flex flex-col gap-2 rounded-md border p-2">
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
    </div>
  );
}
