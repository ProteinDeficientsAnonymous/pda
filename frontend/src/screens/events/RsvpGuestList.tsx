import { useState } from 'react';

import type { Event, EventGuest } from '@/models/event';
import { RsvpServerStatus } from '@/models/event';

import { GuestListDialog, type GuestTab } from './GuestListDialog';
import { countWithPlusOnes, PREVIEW_LIMIT, previewGuests } from './guestSort';

interface Props {
  event: Event;
  canSeeInvited: boolean;
  token?: string;
}

export function RsvpGuestList({ event, canSeeInvited, token }: Props) {
  const [openTab, setOpenTab] = useState<GuestTab | null>(null);

  const going = event.guests.filter((g) => g.status === RsvpServerStatus.Attending);
  const maybe = event.guests.filter((g) => g.status === RsvpServerStatus.Maybe);
  const goingCount = countWithPlusOnes(going);
  const maybeCount = countWithPlusOnes(maybe);

  if (goingCount === 0 && maybeCount === 0) {
    const guestListHidden = event.guests.length === 0 && event.attendingCount > 0;
    return (
      <p className="text-muted text-xs">
        {guestListHidden ? "rsvp to see who's going" : 'no one yet'}
      </p>
    );
  }

  const preview = previewGuests([...going, ...maybe], PREVIEW_LIMIT);
  const overflow = going.length + maybe.length - preview.length;

  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-foreground-secondary text-sm">
          {goingCount} going
          {maybeCount > 0 ? <span className="text-muted"> · {maybeCount} maybe</span> : null}
        </p>
        <button
          type="button"
          onClick={() => {
            setOpenTab('going');
          }}
          className="text-brand-600 hover:bg-surface-dim rounded-full px-2 py-1 text-sm"
        >
          view all
        </button>
      </div>

      <div className="flex items-center gap-1.5">
        {preview.map((g) => (
          <PreviewAvatar key={g.userId} guest={g} />
        ))}
        {overflow > 0 ? (
          <button
            type="button"
            onClick={() => {
              setOpenTab('going');
            }}
            aria-label={`view all ${String(going.length + maybe.length)} guests`}
            className="bg-surface-dim text-foreground-secondary hover:bg-surface-dim/70 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[11px]"
          >
            +{overflow}
          </button>
        ) : null}
      </div>

      {openTab ? (
        <GuestListDialog
          event={event}
          canSeeInvited={canSeeInvited}
          initialTab={openTab}
          {...(token ? { token } : {})}
          onClose={() => {
            setOpenTab(null);
          }}
        />
      ) : null}
    </div>
  );
}

function PreviewAvatar({ guest }: { guest: EventGuest }) {
  if (guest.photoUrl) {
    return (
      <img
        src={guest.photoUrl}
        alt={guest.name}
        title={guest.name}
        loading="lazy"
        className="h-8 w-8 shrink-0 rounded-full object-cover"
      />
    );
  }
  return (
    <span
      title={guest.name}
      aria-label={guest.name}
      className="bg-toggle-off text-foreground-secondary flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs"
    >
      {guest.name.slice(0, 1).toLowerCase()}
    </span>
  );
}
