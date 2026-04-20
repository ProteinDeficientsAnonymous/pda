// Add co-hosts to an event from the event detail view. Hosts + existing
// co-hosts can open this from the hosts section.

import { isAxiosError } from 'axios';
import { useState } from 'react';
import { useUpdateEvent } from '@/api/eventWrites';
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

export function AddCoHostDialog({ event, open, onClose }: Props) {
  const update = useUpdateEvent(event.id);
  const [added, setAdded] = useState<MemberSearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    const combined = Array.from(new Set([...event.coHostIds, ...added.map((m) => m.id)]));
    try {
      await update.mutateAsync({ coHostIds: combined });
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
        excludeIds={[
          ...(event.createdById ? [event.createdById] : []),
          ...event.coHostIds,
        ]}
      />
      {error ? (
        <p role="alert" className="mt-2 text-sm text-destructive">
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
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't add co-hosts — try again";
}
