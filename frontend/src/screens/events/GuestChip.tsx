import { Link } from 'react-router-dom';

import type { Event, EventGuest } from '@/models/event';
import { AttendanceStatus } from '@/models/event';

export function GuestChip({ guest }: { guest: EventGuest }) {
  const content = (
    <>
      {guest.photoUrl ? (
        <img
          src={guest.photoUrl}
          alt=""
          className="h-5 w-5 rounded-full object-cover"
          loading="lazy"
        />
      ) : (
        <span
          aria-hidden="true"
          className="bg-toggle-off text-foreground-secondary flex h-5 w-5 items-center justify-center rounded-full text-[10px]"
        >
          {guest.name.slice(0, 1).toLowerCase()}
        </span>
      )}
      {guest.name}
      {guest.hasPlusOne ? <span className="text-muted">+1</span> : null}
    </>
  );

  if (!guest.isMember) {
    return (
      <span
        className="bg-surface-dim/60 text-foreground-secondary inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs opacity-60 grayscale"
        title={`${guest.name} (not a member)`}
        aria-label={`${guest.name} (not a member)`}
      >
        {content}
      </span>
    );
  }

  return (
    <Link
      to={`/members/${guest.userId}`}
      className="bg-surface-dim hover:bg-surface-dim/70 inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs"
      title={guest.name}
    >
      {content}
    </Link>
  );
}

export function InvitedList({ event }: { event: Event }) {
  if (event.invitedUserIds.length === 0) {
    return <p className="text-muted text-xs">no one invited yet</p>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {event.invitedUserIds.map((id, i) => {
        const name = event.invitedUserNames[i] ?? 'member';
        const photoUrl = event.invitedUserPhotoUrls[i] ?? '';
        return (
          <GuestChip
            key={id}
            guest={{
              userId: id,
              name,
              status: 'invited',
              phone: null,
              photoUrl,
              hasPlusOne: false,
              attendance: AttendanceStatus.Unknown,
              isMember: true,
              paidConfirmed: false,
            }}
          />
        );
      })}
    </div>
  );
}
