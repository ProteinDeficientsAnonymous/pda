import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useSetGuestRsvp } from '@/api/eventStats';
import { Dialog } from '@/components/ui/Dialog';
import { RsvpStatusPicker } from '@/components/ui/RsvpStatusPicker';
import type { Event, EventGuest, RsvpInputStatus } from '@/models/event';
import { AttendanceStatus, isRsvpInputStatus, RsvpServerStatus } from '@/models/event';
import { cn } from '@/utils/cn';

type Tab = 'going' | 'maybe' | 'cant' | 'waitlist' | 'invited';

function countWithPlusOnes(guests: EventGuest[]): number {
  return guests.reduce((acc, g) => acc + 1 + (g.hasPlusOne ? 1 : 0), 0);
}

function bucket(guests: EventGuest[]): Record<Tab, EventGuest[]> {
  return {
    going: guests.filter((g) => g.status === RsvpServerStatus.Attending),
    maybe: guests.filter((g) => g.status === RsvpServerStatus.Maybe),
    cant: guests.filter((g) => g.status === RsvpServerStatus.CantGo),
    waitlist: guests.filter((g) => g.status === RsvpServerStatus.Waitlisted),
    invited: [],
  };
}

interface Props {
  event: Event;
  canSeeInvited: boolean;
  canManageRsvps?: boolean;
}

export function RsvpGuestList({ event, canSeeInvited, canManageRsvps = false }: Props) {
  const buckets = useMemo(() => bucket(event.guests), [event.guests]);
  const counts: Record<Tab, number> = {
    going: countWithPlusOnes(buckets.going),
    maybe: countWithPlusOnes(buckets.maybe),
    cant: countWithPlusOnes(buckets.cant),
    waitlist: countWithPlusOnes(buckets.waitlist),
    invited: canSeeInvited ? event.invitedCount : 0,
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'going', label: 'going' },
    { key: 'maybe', label: 'maybe' },
    { key: 'cant', label: "can't go" },
  ];
  if (counts.waitlist > 0) tabs.push({ key: 'waitlist', label: 'waitlist' });
  if (canSeeInvited) tabs.push({ key: 'invited', label: 'invited' });

  const defaultTab = tabs.find((t) => counts[t.key] > 0)?.key ?? 'going';
  const [active, setActive] = useState<Tab>(defaultTab);
  const visible = active === 'invited' ? [] : buckets[active];

  if (tabs.every((t) => counts[t.key] === 0)) {
    return <p className="text-muted text-xs">no one yet</p>;
  }

  return (
    <div>
      <div
        role="tablist"
        aria-label="guest status"
        className="border-border-strong bg-surface mb-2 flex w-full rounded-full border p-1"
      >
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={active === t.key}
            onClick={() => {
              setActive(t.key);
            }}
            className={cn(
              'inline-flex flex-1 flex-col items-center justify-center rounded-full px-2 py-1 text-sm leading-tight whitespace-nowrap transition-colors',
              active === t.key
                ? 'bg-brand-600 text-brand-on'
                : 'text-foreground-secondary hover:bg-surface-dim',
            )}
          >
            <span>{t.label}</span>
            <span className="text-xs opacity-80">{counts[t.key]}</span>
          </button>
        ))}
      </div>
      {active === 'invited' ? (
        <InvitedList event={event} />
      ) : (
        <div className="flex flex-wrap gap-2">
          {visible.map((g) => (
            <GuestChip key={g.userId} guest={g} eventId={event.id} canEdit={canManageRsvps} />
          ))}
        </div>
      )}
    </div>
  );
}

function GuestChip({
  guest,
  eventId,
  canEdit = false,
}: {
  guest: EventGuest;
  eventId?: string;
  canEdit?: boolean;
}) {
  const [editOpen, setEditOpen] = useState(false);

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
    <span className="bg-surface-dim hover:bg-surface-dim/70 inline-flex items-center gap-1 rounded-full pr-1 text-xs">
      <Link
        to={`/members/${guest.userId}`}
        className="inline-flex items-center gap-1.5 py-1 pl-2"
        title={guest.name}
      >
        {content}
      </Link>
      {canEdit && eventId ? (
        <>
          <button
            type="button"
            aria-label={`change ${guest.name}'s rsvp`}
            onClick={() => {
              setEditOpen(true);
            }}
            className="text-muted hover:text-foreground px-1"
          >
            edit
          </button>
          <EditGuestRsvpDialog
            eventId={eventId}
            guest={guest}
            open={editOpen}
            onClose={() => {
              setEditOpen(false);
            }}
          />
        </>
      ) : null}
    </span>
  );
}

function EditGuestRsvpDialog({
  eventId,
  guest,
  open,
  onClose,
}: {
  eventId: string;
  guest: EventGuest;
  open: boolean;
  onClose: () => void;
}) {
  const setGuestRsvp = useSetGuestRsvp(eventId);
  const currentStatus = isRsvpInputStatus(guest.status) ? guest.status : null;

  function changeStatus(status: RsvpInputStatus) {
    setGuestRsvp.mutate(
      { userId: guest.userId, status, hasPlusOne: guest.hasPlusOne },
      {
        onSuccess: onClose,
        onError: (err) => {
          toast.error(extractApiErrorOr(err, "couldn't update their rsvp — try again"));
        },
      },
    );
  }

  return (
    <Dialog open={open} onClose={onClose} title={`${guest.name}'s rsvp`}>
      <RsvpStatusPicker
        value={currentStatus}
        disabled={setGuestRsvp.isPending}
        onSelect={changeStatus}
      />
    </Dialog>
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
            }}
          />
        );
      })}
    </div>
  );
}
