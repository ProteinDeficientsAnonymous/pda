// RSVP toggle. Three pills (going / maybe / can't) + optional +1 toggle.
// Semantics intentionally mirror rsvp_section.dart:
//   - tap an active pill to remove the RSVP entirely
//   - tap going while at capacity → server auto-waitlists you
//   - +1 is a second POST with the same status + hasPlusOne: true
//   - waitlisted state shows only "leave waitlist" (no maybe/can't pills)

import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useRemoveRsvp, useSetRsvp } from '@/api/rsvp';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { RsvpStatusPicker } from '@/components/ui/RsvpStatusPicker';
import {
  type Event,
  type RsvpInputStatus,
  RsvpServerStatus,
  RsvpStatus,
  spotsLeft,
} from '@/models/event';

import { RsvpGuestList } from './RsvpGuestList';

interface Props {
  event: Event;
  canSeeInvited: boolean;
}

export function RsvpSection({ event, canSeeInvited }: Props) {
  const setRsvp = useSetRsvp();
  const removeRsvp = useRemoveRsvp();
  const myUserId = useAuthStore((s) => s.user?.id);
  const [error, setError] = useState<string | null>(null);

  const myRsvp = event.myRsvp;
  const onWaitlist = myRsvp === RsvpServerStatus.Waitlisted;
  // Match by user id, not status — multiple guests share the same status,
  // so a status match returns some other attendee's record and the +1
  // toggle reflects the wrong user (issue #368).
  const myGuest = event.guests.find((g) => g.userId === myUserId);
  const hasPlusOne = myGuest?.hasPlusOne ?? false;
  const atCapacity = spotsLeft(event) === 0;

  async function removeMyRsvp() {
    setError(null);
    try {
      await removeRsvp.mutateAsync(event.id);
    } catch (err) {
      setError(extractError(err));
    }
  }

  async function apply(next: RsvpInputStatus) {
    if (next === myRsvp) {
      await removeMyRsvp();
      return;
    }
    setError(null);
    try {
      await setRsvp.mutateAsync({ eventId: event.id, status: next });
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
        status: myRsvp as RsvpInputStatus,
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
        <WaitlistView onLeave={() => void removeMyRsvp()} busy={busy} />
      ) : (
        <>
          <RsvpStatusPicker
            value={myRsvp}
            disabled={busy}
            onSelect={(status) => void apply(status)}
            labelFor={(status, def) =>
              status === RsvpStatus.Attending && atCapacity && myRsvp !== RsvpServerStatus.Attending
                ? 'join the waitlist'
                : def
            }
          />
          <SpotsLeft event={event} />
          {event.allowPlusOnes &&
          (myRsvp === RsvpServerStatus.Attending || myRsvp === RsvpServerStatus.Maybe) ? (
            <div className="flex justify-center">
              <Button variant="secondary" onClick={() => void togglePlusOne()} disabled={busy}>
                {hasPlusOne ? 'remove +1' : 'bring a +1'}
              </Button>
            </div>
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

function SpotsLeft({ event }: { event: Event }) {
  const left = spotsLeft(event);
  if (left === null || left === 0) return null;
  return (
    <p className="text-warning text-center text-xs">
      {left === 1 ? '1 spot left' : `${String(left)} spots left`}
    </p>
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
  return extractApiErrorOr(err, "couldn't update your rsvp — try again");
}
