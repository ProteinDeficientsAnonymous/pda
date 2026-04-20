// RSVP toggle. Three pills (going / maybe / can't) + optional +1 toggle.
// Semantics intentionally mirror rsvp_section.dart:
//   - tap an active pill to remove the RSVP entirely
//   - tap going while at capacity → server auto-waitlists you
//   - +1 is a second POST with the same status + hasPlusOne: true
//   - waitlisted state shows only "leave waitlist" (no maybe/can't pills)

import { isAxiosError } from 'axios';
import { useState } from 'react';
import { RsvpStatus, RsvpServerStatus, type Event } from '@/models/event';
import { useRemoveRsvp, useSetRsvp } from '@/api/rsvp';
import { Button } from '@/components/ui/Button';
import { cn } from '@/utils/cn';
import { RsvpGuestList } from './RsvpGuestList';

interface Props {
  event: Event;
  canSeeInvited: boolean;
}

type InputStatus = (typeof RsvpStatus)[keyof typeof RsvpStatus];

const PILLS: { status: InputStatus; label: string }[] = [
  { status: RsvpStatus.Attending, label: "i'm going" },
  { status: RsvpStatus.Maybe, label: 'maybe' },
  { status: RsvpStatus.CantGo, label: "can't go" },
];

export function RsvpSection({ event, canSeeInvited }: Props) {
  const setRsvp = useSetRsvp();
  const removeRsvp = useRemoveRsvp();
  const [error, setError] = useState<string | null>(null);

  const myRsvp = event.myRsvp;
  const onWaitlist = myRsvp === RsvpServerStatus.Waitlisted;
  const myGuest = event.guests.find((g) => g.status === myRsvp);
  const hasPlusOne = myGuest?.hasPlusOne ?? false;
  const atCapacity = event.maxAttendees !== null && event.attendingCount >= event.maxAttendees;

  async function apply(next: InputStatus) {
    setError(null);
    try {
      if (next === myRsvp) {
        await removeRsvp.mutateAsync(event.id);
      } else {
        await setRsvp.mutateAsync({ eventId: event.id, status: next });
      }
    } catch (err) {
      setError(extractError(err));
    }
  }

  async function togglePlusOne() {
    if (!myRsvp || onWaitlist) return;
    // Only attending/maybe can bring a +1 (server-enforced on attending; UI
    // gate prevents the extra POST in the first place).
    if (myRsvp !== RsvpServerStatus.Attending && myRsvp !== RsvpServerStatus.Maybe) return;
    setError(null);
    try {
      await setRsvp.mutateAsync({
        eventId: event.id,
        status: myRsvp as InputStatus,
        hasPlusOne: !hasPlusOne,
      });
    } catch (err) {
      setError(extractError(err));
    }
  }

  const busy = setRsvp.isPending || removeRsvp.isPending;

  return (
    <section aria-label="rsvp" className="flex flex-col gap-3">
      {onWaitlist ? (
        <WaitlistView
          onLeave={() => {
            void removeRsvp.mutateAsync(event.id);
          }}
          busy={busy}
        />
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            {PILLS.map((p) => (
              <RsvpPill
                key={p.status}
                label={p.label}
                active={myRsvp === p.status}
                disabled={busy}
                onClick={() => void apply(p.status)}
              />
            ))}
          </div>
          {atCapacity && myRsvp !== RsvpServerStatus.Attending ? (
            <p className="text-warning text-xs">
              event is full — tapping "i'm going" adds you to the waitlist
            </p>
          ) : null}
          {event.allowPlusOnes &&
          (myRsvp === RsvpServerStatus.Attending || myRsvp === RsvpServerStatus.Maybe) ? (
            <Button variant="secondary" onClick={() => void togglePlusOne()} disabled={busy}>
              {hasPlusOne ? 'remove +1' : 'bring a +1'}
            </Button>
          ) : null}
        </>
      )}

      <Summary event={event} />
      {error ? (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      ) : null}

      <div className="mt-2">
        <RsvpGuestList event={event} canSeeInvited={canSeeInvited} />
      </div>
    </section>
  );
}

function RsvpPill({
  label,
  active,
  disabled,
  onClick,
}: {
  label: string;
  active: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'inline-flex h-10 items-center rounded-full px-4 text-sm font-medium transition-colors disabled:cursor-not-allowed',
        active
          ? 'bg-brand-600 text-brand-on'
          : 'border-border-strong text-foreground-secondary hover:bg-background border',
        disabled && 'opacity-60',
      )}
    >
      {label}
    </button>
  );
}

function WaitlistView({ onLeave, busy }: { onLeave: () => void; busy: boolean }) {
  return (
    <div className="flex items-center gap-3 rounded-md bg-amber-50 px-3 py-2">
      <span className="text-warning text-sm">you're on the waitlist</span>
      <Button variant="ghost" onClick={onLeave} disabled={busy}>
        leave waitlist
      </Button>
    </div>
  );
}

function Summary({ event }: { event: Event }) {
  const parts: string[] = [];
  if (event.maxAttendees !== null) {
    parts.push(`${String(event.attendingCount)} / ${String(event.maxAttendees)} going`);
  } else {
    parts.push(`${String(event.attendingCount)} going`);
  }
  if (event.waitlistedCount > 0) parts.push(`${String(event.waitlistedCount)} waitlisted`);
  return <p className="text-muted text-xs">{parts.join(' · ')}</p>;
}

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't update your rsvp — try again";
}
