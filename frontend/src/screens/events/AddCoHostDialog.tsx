import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useAddCohosts } from '@/api/cohostInvites';
import type { MemberSearchResult } from '@/api/userSearch';
import { MemberPicker } from '@/components/MemberPicker';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import type { Event } from '@/models/event';

interface Props {
  event: Event;
  open: boolean;
  onClose: () => void;
}

export function AddCoHostDialog({ event, open, onClose }: Props) {
  const update = useAddCohosts();
  const [added, setAdded] = useState<MemberSearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const excludeIds = [
    ...event.coHostIds,
    ...event.pendingCohostInvites.map((invite) => invite.userId),
  ];

  async function submit() {
    setError(null);
    try {
      await update.mutateAsync({ eventId: event.id, userIds: added.map((m) => m.id) });
      setAdded([]);
      onClose();
    } catch (err) {
      setError(extractError(err));
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="add co-hosts">
      <MemberPicker
        label="search members"
        selected={added}
        onChange={setAdded}
        excludeIds={excludeIds}
      />
      {error ? (
        <p role="alert" className="text-destructive mt-2 text-sm">
          {error}
        </p>
      ) : null}
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose} disabled={update.isPending}>
          cancel
        </Button>
        <Button onClick={() => void submit()} disabled={update.isPending || added.length === 0}>
          {update.isPending ? 'adding…' : `add ${String(added.length)}`}
        </Button>
      </div>
    </Dialog>
  );
}

function extractError(err: unknown): string {
  return extractApiErrorOr(err, "couldn't add co-hosts — try again");
}
