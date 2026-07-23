import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useRemoveGuestRsvp, useSetGuestRsvp } from '@/api/eventStats';
import { RsvpStatusPicker } from '@/components/ui/RsvpStatusPicker';
import type { Event, EventGuest, RsvpInputStatus } from '@/models/event';
import { isRsvpInputStatus, RsvpServerStatus } from '@/models/event';

const GROUPS: {
  status: (typeof RsvpServerStatus)[keyof typeof RsvpServerStatus];
  label: string;
}[] = [
  { status: RsvpServerStatus.Attending, label: 'going' },
  { status: RsvpServerStatus.Maybe, label: 'maybe' },
  { status: RsvpServerStatus.CantGo, label: "can't go" },
  { status: RsvpServerStatus.Waitlisted, label: 'waitlist' },
];

export function EventManageRsvpsPanel({ event }: { event: Event }) {
  const setGuestRsvp = useSetGuestRsvp(event.id);
  const removeGuestRsvp = useRemoveGuestRsvp(event.id);

  if (event.guests.length === 0) {
    return <p className="text-muted text-sm">no one yet 🌿</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      {GROUPS.map((group) => {
        const guests = event.guests.filter((g) => g.status === group.status);
        if (guests.length === 0) return null;
        return (
          <GuestGroup
            key={group.status}
            label={group.label}
            guests={guests}
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
            isPending={setGuestRsvp.isPending || removeGuestRsvp.isPending}
          />
        );
      })}
    </div>
  );
}

function GuestGroup({
  label,
  guests,
  onChangeStatus,
  onRemove,
  isPending,
}: {
  label: string;
  guests: EventGuest[];
  onChangeStatus: (userId: string, status: RsvpInputStatus, hasPlusOne: boolean) => void;
  onRemove: (userId: string) => void;
  isPending: boolean;
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
            onChangeStatus={onChangeStatus}
            onRemove={onRemove}
            isPending={isPending}
          />
        ))}
      </ul>
    </div>
  );
}

function GuestRow({
  guest,
  onChangeStatus,
  onRemove,
  isPending,
}: {
  guest: EventGuest;
  onChangeStatus: (userId: string, status: RsvpInputStatus, hasPlusOne: boolean) => void;
  onRemove: (userId: string) => void;
  isPending: boolean;
}) {
  const currentStatus = isRsvpInputStatus(guest.status) ? guest.status : null;

  if (!guest.isMember) {
    return (
      <li className="border-border flex items-center justify-between gap-2 rounded-md border p-2 opacity-60">
        <span className="text-foreground text-sm">{guest.name} (not a member)</span>
      </li>
    );
  }

  return (
    <li className="border-border flex flex-col gap-2 rounded-md border p-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-foreground text-sm">{guest.name}</span>
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
