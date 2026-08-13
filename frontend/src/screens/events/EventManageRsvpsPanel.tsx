import { useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import { mergeEventGuestPhotos } from '@/api/eventMapper';
import { useEventGuests } from '@/api/events';
import { useRemoveGuestRsvp, useSetGuestPayment, useSetGuestRsvp } from '@/api/eventStats';
import type { MemberSearchResult } from '@/api/userSearch';
import { MemberPicker } from '@/components/MemberPicker';
import { Button } from '@/components/ui/Button';
import { RsvpStatusPicker } from '@/components/ui/RsvpStatusPicker';
import type { Event, EventGuest, RsvpInputStatus } from '@/models/event';
import { isRsvpInputStatus, RSVP_GROUP_LABELS, RsvpServerStatus } from '@/models/event';
import { cn } from '@/utils/cn';
import { eventRequiresPaymentConfirmation } from '@/utils/eventCost';

import { EventRsvpResponsesSection } from './EventRsvpResponsesSection';

export function EventManageRsvpsPanel({
  event,
  readOnly = false,
}: {
  event: Event;
  /** Past events: hide add/edit controls; still show question responses. */
  readOnly?: boolean;
}) {
  const setGuestRsvp = useSetGuestRsvp(event.id);
  const removeGuestRsvp = useRemoveGuestRsvp(event.id);
  const setGuestPayment = useSetGuestPayment(event.id);
  const showPaymentStatus = !readOnly && eventRequiresPaymentConfirmation(event);
  const { data: withPhotos } = useEventGuests(event.id);
  const displayEvent = mergeEventGuestPhotos(event, withPhotos);

  return (
    <div className="flex flex-col gap-8">
      {readOnly ? null : (
        <AddMemberSection
          event={event}
          isPending={setGuestRsvp.isPending}
          onAdd={(userId) => {
            setGuestRsvp.mutate(
              { userId, status: RsvpServerStatus.Attending, hasPlusOne: false },
              {
                onError: (err) => {
                  toast.error(extractApiErrorOr(err, "couldn't add them — try again"));
                },
              },
            );
          }}
        />
      )}
      {displayEvent.guests.length === 0 ? (
        <p className="text-muted text-sm">no one yet 🌿</p>
      ) : (
        RSVP_GROUP_LABELS.map((group) => {
          const guests = displayEvent.guests.filter((g) => g.status === group.status);
          if (guests.length === 0) return null;
          return (
            <GuestGroup
              key={group.status}
              label={group.label}
              guests={guests}
              readOnly={readOnly}
              onChangeStatus={(userId, status, hasPlusOne) => {
                setGuestRsvp.mutate(
                  { userId, status, hasPlusOne },
                  {
                    onError: (err) => {
                      toast.error(extractApiErrorOr(err, "couldn't update their rsvp — try again"));
                    },
                  },
                );
              }}
              onRemove={(userId) => {
                removeGuestRsvp.mutate(
                  { userId },
                  {
                    onError: (err) => {
                      toast.error(extractApiErrorOr(err, "couldn't remove them — try again"));
                    },
                  },
                );
              }}
              onTogglePaid={
                showPaymentStatus
                  ? (userId, paidConfirmed) => {
                      setGuestPayment.mutate(
                        { userId, paidConfirmed },
                        {
                          onError: (err) => {
                            toast.error(
                              extractApiErrorOr(err, "couldn't update payment — try again"),
                            );
                          },
                        },
                      );
                    }
                  : undefined
              }
              isPending={
                setGuestRsvp.isPending || removeGuestRsvp.isPending || setGuestPayment.isPending
              }
            />
          );
        })
      )}
      <EventRsvpResponsesSection event={displayEvent} />
    </div>
  );
}

function AddMemberSection({
  event,
  onAdd,
  isPending,
}: {
  event: Event;
  onAdd: (userId: string) => void;
  isPending: boolean;
}) {
  const [picked, setPicked] = useState<MemberSearchResult[]>([]);

  function submit() {
    picked.forEach((m) => {
      onAdd(m.id);
    });
    setPicked([]);
  }

  return (
    <div className="border-border flex flex-col gap-2 rounded-md border p-3">
      <MemberPicker
        label="add a member"
        selected={picked}
        onChange={setPicked}
        excludeIds={event.guests.map((g) => g.userId)}
      />
      {picked.length > 0 ? (
        <Button onClick={submit} disabled={isPending} className="self-end">
          {isPending ? 'adding…' : 'add'}
        </Button>
      ) : null}
    </div>
  );
}

function GuestGroup({
  label,
  guests,
  onChangeStatus,
  onRemove,
  onTogglePaid,
  isPending,
  readOnly,
}: {
  label: string;
  guests: EventGuest[];
  onChangeStatus: (userId: string, status: RsvpInputStatus, hasPlusOne: boolean) => void;
  onRemove: (userId: string) => void;
  onTogglePaid?: ((userId: string, paidConfirmed: boolean) => void) | undefined;
  isPending: boolean;
  readOnly: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-muted text-xs font-medium">
        {label} ({guests.length})
      </h2>
      <ul className="flex flex-col gap-2">
        {guests.map((g) => (
          <GuestRow
            key={g.userId}
            guest={g}
            readOnly={readOnly}
            onChangeStatus={onChangeStatus}
            onRemove={onRemove}
            onTogglePaid={onTogglePaid}
            isPending={isPending}
          />
        ))}
      </ul>
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
      <li className="border-border flex items-center justify-between gap-2 rounded-md border p-2">
        <span className="text-foreground text-sm">
          {guest.name}
          {!guest.isMember ? ' (not a member)' : ''}
        </span>
        <span className="text-muted text-xs">
          {currentStatus ?? guest.status}
          {guest.hasPlusOne ? ' · +1' : ''}
        </span>
      </li>
    );
  }

  if (!guest.isMember) {
    return (
      <li className="border-border flex items-center justify-between gap-2 rounded-md border p-2 opacity-60">
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
    </li>
  );
}
