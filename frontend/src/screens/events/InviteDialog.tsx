// Invite members to an event — calls the dedicated invitations endpoint
// (POST /events/{id}/invitations/), which adds with set-union semantics so
// it can never clobber the existing invitee list. Co-hosts + members (when
// invite_permission=all_members) can invite.

import { useState } from 'react';
import { extractApiErrorOr } from '@/api/apiErrors';
import { useInviteToEvent } from '@/api/eventWrites';
import { MemberPicker } from '@/components/MemberPicker';
import type { MemberSearchResult } from '@/api/userSearch';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import type { Event } from '@/models/event';

interface Props {
  event: Event;
  open: boolean;
  onClose: () => void;
}

export function InviteDialog({ event, open, onClose }: Props) {
  const invite = useInviteToEvent(event.id);
  const [added, setAdded] = useState<MemberSearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    try {
      await invite.mutateAsync(added.map((m) => m.id));
      setAdded([]);
      onClose();
    } catch (err) {
      setError(extractError(err));
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="invite members">
      <MemberPicker
        label="search members"
        selected={added}
        onChange={setAdded}
        excludeIds={[
          ...event.invitedUserIds,
          ...(event.createdById ? [event.createdById] : []),
          ...event.coHostIds,
        ]}
      />
      {error ? (
        <p role="alert" className="text-destructive mt-2 text-sm">
          {error}
        </p>
      ) : null}
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose} disabled={invite.isPending}>
          cancel
        </Button>
        <Button onClick={() => void submit()} disabled={invite.isPending || added.length === 0}>
          {invite.isPending ? 'inviting…' : `invite ${String(added.length)}`}
        </Button>
      </div>
    </Dialog>
  );
}

function extractError(err: unknown): string {
  return extractApiErrorOr(err, "couldn't send invites — try again");
}
