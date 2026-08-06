import { Link } from 'react-router-dom';

import type { Event, EventGuest } from '@/models/event';
import { AttendanceStatus } from '@/models/event';
import { cn } from '@/utils/cn';

export function GuestChip({ guest, row = false }: { guest: EventGuest; row?: boolean }) {
  const avatarSize = row ? 'h-8 w-8 text-xs' : 'h-5 w-5 text-[10px]';
  const content = (
    <>
      {guest.photoUrl ? (
        <img
          src={guest.photoUrl}
          alt=""
          className={cn('shrink-0 rounded-full object-cover', avatarSize)}
          loading="lazy"
        />
      ) : (
        <span
          aria-hidden="true"
          className={cn(
            'bg-toggle-off text-foreground-secondary flex shrink-0 items-center justify-center rounded-full',
            avatarSize,
          )}
        >
          {guest.name.slice(0, 1).toLowerCase()}
        </span>
      )}
      <span className={row ? 'truncate' : undefined}>{guest.name}</span>
      {guest.hasPlusOne ? <span className="text-muted">+1</span> : null}
    </>
  );

  const shape = row
    ? 'flex w-full items-center gap-3 rounded-lg px-2 py-2 text-sm'
    : 'inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs';

  if (!guest.isMember) {
    return (
      <span
        className={cn('bg-surface-dim/60 text-foreground-secondary opacity-60 grayscale', shape)}
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
      className={cn('bg-surface-dim hover:bg-surface-dim/70', shape)}
      title={guest.name}
    >
      {content}
    </Link>
  );
}

export function InvitedList({ event, row = false }: { event: Event; row?: boolean }) {
  if (event.invitedUserIds.length === 0) {
    return <p className="text-muted text-xs">no one invited yet</p>;
  }
  return (
    <div className={row ? 'flex flex-col gap-1' : 'flex flex-wrap gap-2'}>
      {event.invitedUserIds.map((id, i) => {
        const name = event.invitedUserNames[i] ?? 'member';
        const photoUrl = event.invitedUserPhotoUrls[i] ?? '';
        return (
          <GuestChip
            key={id}
            row={row}
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
