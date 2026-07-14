import { useState } from 'react';

import type { Event } from '@/models/event';
import { EventStatus } from '@/models/event';

import { EmailBlastDialog } from './EmailBlastDialog';

interface Props {
  event: Event;
}

export function EmailBlastButton({ event }: Props) {
  const [open, setOpen] = useState(false);

  const canEmailAttendees = event.status !== EventStatus.Draft && event.guests.length > 0;
  if (!canEmailAttendees) return null;

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setOpen(true);
        }}
        aria-label="email blast"
        className="bg-surface-dim text-foreground-secondary hover:bg-surface-dim/70 hover:text-foreground inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors"
      >
        email blast
      </button>
      <EmailBlastDialog
        event={event}
        open={open}
        onClose={() => {
          setOpen(false);
        }}
      />
    </>
  );
}
