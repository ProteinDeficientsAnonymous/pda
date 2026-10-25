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
  onTogglePaymentVerified,
  onReorder,
  isPending,
}: {
  label: string;
  guests: EventGuest[];
  onChangeStatus: (userId: string, status: RsvpInputStatus, hasPlusOne: boolean) => void;
  onRemove: (userId: string) => void;
  onTogglePaymentVerified?: ((userId: string, verified: boolean) => void) | undefined;
  onReorder?: ((userIds: string[]) => void) | undefined;
  isPending: boolean;
}) {
  const row = (g: EventGuest) => (
    <GuestRow
      guest={g}
      onChangeStatus={onChangeStatus}
      onRemove={onRemove}
      onTogglePaymentVerified={onTogglePaymentVerified}
      isPending={isPending}
    />
  );

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-muted text-xs font-medium">
        {label} ({guests.length})
      </h2>
      {onReorder ? (
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

type PaymentState = 'verified' | 'says-paid' | 'unpaid';

const PAYMENT_BADGE: Record<PaymentState, { icon: string; label: string; classes: string }> = {
  verified: { icon: '✓', label: 'verified', classes: 'bg-success-subtle text-success' },
  'says-paid': { icon: '◐', label: 'says paid', classes: 'bg-warning-subtle text-warning' },
  unpaid: { icon: '○', label: 'unpaid', classes: 'bg-surface-dim text-foreground-secondary' },
};

function paymentState(guest: EventGuest): PaymentState {
  if (guest.paymentVerified) return 'verified';
  return guest.paidConfirmed ? 'says-paid' : 'unpaid';
}

function PaymentBadge({
  guest,
  onToggle,
  isPending,
}: {
  guest: EventGuest;
  onToggle: () => void;
  isPending: boolean;
}) {
  const { icon, label, classes } = PAYMENT_BADGE[paymentState(guest)];
  const action = guest.paymentVerified ? 'unverify payment' : 'mark payment verified';
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={isPending}
      aria-pressed={guest.paymentVerified}
      aria-label={`${label}, ${action}`}
      title={action}
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-60',
        classes,
      )}
    >
      <span aria-hidden="true">{icon}</span> {label}
    </button>
  );
}

function GuestRow({
  guest,
  onChangeStatus,
  onRemove,
  onTogglePaymentVerified,
  isPending,
}: {
  guest: EventGuest;
  onChangeStatus: (userId: string, status: RsvpInputStatus, hasPlusOne: boolean) => void;
  onRemove: (userId: string) => void;
  onTogglePaymentVerified?: ((userId: string, verified: boolean) => void) | undefined;
  isPending: boolean;
}) {
  const currentStatus = isRsvpInputStatus(guest.status) ? guest.status : null;

  return (
    <div className="border-border flex flex-col gap-2 rounded-md border p-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-foreground text-sm">
            {guest.name}
            {guest.isMember ? null : <span className="text-muted"> (not a member)</span>}
          </span>
          {onTogglePaymentVerified ? (
            <PaymentBadge
              guest={guest}
              isPending={isPending}
              onToggle={() => {
                onTogglePaymentVerified(guest.userId, !guest.paymentVerified);
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
