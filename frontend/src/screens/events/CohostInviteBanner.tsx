// Accept/decline banner shown to a user with a pending co-host invite for
// this event. Hidden once the invite is resolved or the event is past — the
// banner relies on `myPendingCohostInviteId` from EventOut, which the backend
// clears via lazy expiration once the event ends.

import { toast } from 'sonner';
import { hasErrorCode } from '@/api/apiErrors';
import { useAcceptCohostInvite, useDeclineCohostInvite } from '@/api/cohostInvites';
import { Code } from '@/api/validationCodes';
import { Button } from '@/components/ui/Button';
import type { Event } from '@/models/event';

interface Props {
  event: Event;
}

export function CohostInviteBanner({ event }: Props) {
  const inviteId = event.myPendingCohostInviteId;
  const accept = useAcceptCohostInvite();
  const decline = useDeclineCohostInvite();

  if (!inviteId) return null;
  if (event.isPast) return null;

  const inviterName = event.createdByName ?? 'someone';
  const isWorking = accept.isPending || decline.isPending;

  return (
    <section
      aria-label="co-host invite"
      className="border-highlight-subtle bg-highlight-subtle/40 mt-4 rounded-lg border p-4"
    >
      <p className="text-foreground mb-3 text-sm">
        {inviterName.toLowerCase()} invited you to co-host this event
      </p>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="primary"
          disabled={isWorking}
          onClick={() => {
            accept.mutate(
              { eventId: event.id, inviteId },
              { onError: () => toast.error("couldn't accept — try again") },
            );
          }}
        >
          accept
        </Button>
        <Button
          variant="secondary"
          disabled={isWorking}
          onClick={() => {
            decline.mutate(
              { eventId: event.id, inviteId },
              {
                onError: (err) => {
                  // not_pending means someone (e.g. inviter rescinding) raced us.
                  // Treat as success — the banner will disappear on the next refetch.
                  if (hasErrorCode(err, Code.CoHostInvite.NotPending)) return;
                  toast.error("couldn't decline — try again");
                },
              },
            );
          }}
        >
          decline
        </Button>
      </div>
    </section>
  );
}
