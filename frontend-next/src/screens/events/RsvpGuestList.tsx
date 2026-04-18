// Inline guest list — not a modal. Tabs by status (going / maybe / can't /
// waitlist / invited) and renders GuestChip pills.

import { useMemo, useState } from 'react';
import { cn } from '@/utils/cn';
import type { Event, EventGuest } from '@/models/event';
import { RsvpServerStatus } from '@/models/event';

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
}

export function RsvpGuestList({ event, canSeeInvited }: Props) {
  const buckets = useMemo(() => bucket(event.guests), [event.guests]);
  const counts: Record<Tab, number> = {
    going: countWithPlusOnes(buckets.going),
    maybe: countWithPlusOnes(buckets.maybe),
    cant: countWithPlusOnes(buckets.cant),
    waitlist: countWithPlusOnes(buckets.waitlist),
    invited: canSeeInvited ? event.invitedCount : 0,
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'going', label: `going (${String(counts.going)})` },
    { key: 'maybe', label: `maybe (${String(counts.maybe)})` },
    { key: 'cant', label: `can't (${String(counts.cant)})` },
  ];
  if (counts.waitlist > 0)
    tabs.push({ key: 'waitlist', label: `waitlist (${String(counts.waitlist)})` });
  if (canSeeInvited) tabs.push({ key: 'invited', label: `invited (${String(counts.invited)})` });

  const defaultTab = tabs.find((t) => counts[t.key] > 0)?.key ?? 'going';
  const [active, setActive] = useState<Tab>(defaultTab);
  const visible = active === 'invited' ? [] : buckets[active];

  if (tabs.every((t) => counts[t.key] === 0)) {
    return <p className="text-xs text-neutral-500">no one yet</p>;
  }

  return (
    <div>
      <div role="tablist" aria-label="guest status" className="mb-2 flex flex-wrap gap-1">
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
              'rounded-full px-3 py-1 text-xs transition-colors',
              active === t.key
                ? 'bg-neutral-900 text-white'
                : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200',
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      {active === 'invited' ? (
        <InvitedList event={event} />
      ) : (
        <div className="flex flex-wrap gap-2">
          {visible.map((g) => (
            <GuestChip key={g.userId} guest={g} />
          ))}
        </div>
      )}
    </div>
  );
}

function GuestChip({ guest }: { guest: EventGuest }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full bg-neutral-100 px-2 py-1 text-xs"
      title={guest.name}
    >
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
          className="flex h-5 w-5 items-center justify-center rounded-full bg-neutral-300 text-[10px] text-neutral-700"
        >
          {guest.name.slice(0, 1).toUpperCase()}
        </span>
      )}
      {guest.name}
      {guest.hasPlusOne ? <span className="text-neutral-500">+1</span> : null}
    </span>
  );
}

function InvitedList({ event }: { event: Event }) {
  if (event.invitedUserIds.length === 0) {
    return <p className="text-xs text-neutral-500">no one invited yet</p>;
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
            }}
          />
        );
      })}
    </div>
  );
}
