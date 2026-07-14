import { useState } from 'react';

import type { Event } from '@/models/event';

import { GroupTextDialog } from './GroupTextDialog';

interface Props {
  event: Event;
}

export function GroupTextButton({ event }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setOpen(true);
        }}
        aria-label="group text"
        className="bg-surface-dim text-foreground-secondary hover:bg-surface-dim/70 hover:text-foreground inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors"
      >
        group text
      </button>
      <GroupTextDialog
        eventId={event.id}
        open={open}
        onClose={() => {
          setOpen(false);
        }}
      />
    </>
  );
}
