import { useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  useRemoveGuestRsvp,
  useReorderWaitlist,
  useSetGuestPayment,
  useSetGuestRsvp,
} from '@/api/eventStats';
import type { MemberSearchResult } from '@/api/userSearch';
import { MemberPicker } from '@/components/MemberPicker';
import { Button } from '@/components/ui/Button';
import type { Event } from '@/models/event';
import { RSVP_GROUP_LABELS, RsvpServerStatus } from '@/models/event';
import { eventRequiresPaymentConfirmation } from '@/utils/eventCost';

import { GuestGroup } from './ManageGuestGroup';

export function EventManageRsvpsPanel({ event }: { event: Event }) {
  const setGuestRsvp = useSetGuestRsvp(event.id);
  const removeGuestRsvp = useRemoveGuestRsvp(event.id);
  const setGuestPayment = useSetGuestPayment(event.id);
  const reorderWaitlist = useReorderWaitlist(event.id);
  const showPaymentStatus = eventRequiresPaymentConfirmation(event);

  return (
    <div className="flex flex-col gap-8">
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
      {event.guests.length === 0 ? (
        <p className="text-muted text-sm">no one yet 🌿</p>
      ) : (
        RSVP_GROUP_LABELS.map((group) => {
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
              onReorder={
                group.status === RsvpServerStatus.Waitlisted
                  ? (userIds) => {
                      reorderWaitlist.mutate(
                        { userIds },
                        {
                          onError: (err) => {
                            toast.error(
                              extractApiErrorOr(err, "couldn't reorder the waitlist — try again"),
                            );
                          },
                        },
                      );
                    }
                  : undefined
              }
              isPending={
                setGuestRsvp.isPending ||
                removeGuestRsvp.isPending ||
                setGuestPayment.isPending ||
                reorderWaitlist.isPending
              }
            />
          );
        })
      )}
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
