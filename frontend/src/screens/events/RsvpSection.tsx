// RSVP section. Partiful-style flow (issue #297):
//   - before RSVPing: three pills (going / maybe / can't) that open the
//     RsvpBox in `create` mode
//   - after RSVPing: a status line + "edit RSVP" button that opens the box
//     in `edit` mode (status + +1 only; note is a one-time post, not
//     re-editable — see RsvpNoteField)
//   - waitlisted state shows only "leave waitlist" (no pills/status line)

import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useRemoveRsvp, useSetRsvp } from '@/api/rsvp';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { type Event, RsvpServerStatus, RsvpStatus, spotsLeft } from '@/models/event';

import { RsvpBox } from './RsvpBox';
import { RsvpGuestList } from './RsvpGuestList';

interface Props {
  event: Event;
  canSeeInvited: boolean;
}

type InputStatus = (typeof RsvpStatus)[keyof typeof RsvpStatus];

// `waitlisted` is server-assigned and not a valid input status, so anything
// that re-POSTs an existing RSVP (box edit) needs this narrowing.
function asInputStatus(status: string | null): InputStatus | null {
  const match = Object.values(RsvpStatus).find((s) => s === status);
  return match ?? null;
}

function statusLine(status: InputStatus): string {
  if (status === RsvpStatus.Attending) return "you're going";
  if (status === RsvpStatus.Maybe) return "you're a maybe";
  return "you can't go";
}

const PILLS: { status: InputStatus; label: string }[] = [
  { status: RsvpStatus.Attending, label: "i'm going" },
  { status: RsvpStatus.Maybe, label: 'maybe' },
  { status: RsvpStatus.CantGo, label: "can't go" },
];

interface BoxState {
  mode: 'create' | 'edit';
  initialStatus: InputStatus;
}

export function RsvpSection({ event, canSeeInvited }: Props) {
  const setRsvp = useSetRsvp();
  const removeRsvp = useRemoveRsvp();
  const myUserId = useAuthStore((s) => s.user?.id);
  const [error, setError] = useState<string | null>(null);
  const [box, setBox] = useState<BoxState | null>(null);

  const myRsvp = event.myRsvp;
  const onWaitlist = myRsvp === RsvpServerStatus.Waitlisted;
  const myInputStatus = asInputStatus(myRsvp);
  // Match by user id, not status — multiple guests share the same status,
  // so a status match returns some other attendee's record and the +1
  // toggle reflects the wrong user (issue #368).
  const myGuest = event.guests.find((g) => g.userId === myUserId);
  const hasPlusOne = myGuest?.hasPlusOne ?? false;
  const atCapacity = spotsLeft(event) === 0;

  async function confirmRsvp(args: { status: InputStatus; note?: string; hasPlusOne: boolean }) {
    setError(null);
    try {
      await setRsvp.mutateAsync({
        eventId: event.id,
        status: args.status,
        hasPlusOne: args.hasPlusOne,
        ...(args.note === undefined ? {} : { note: args.note }),
      });
      setBox(null);
    } catch (err) {
      setError(extractError(err));
    }
  }

  async function leaveWaitlist() {
    setError(null);
    try {
      await removeRsvp.mutateAsync(event.id);
    } catch (err) {
      setError(extractError(err));
    }
  }

  const busy = setRsvp.isPending || removeRsvp.isPending;

  return (
    <section aria-label="rsvp" className="flex flex-col gap-3">
      {onWaitlist ? (
        <WaitlistView onLeave={() => void leaveWaitlist()} busy={busy} />
      ) : (
        <RsvpControls
          myInputStatus={myInputStatus}
          atCapacity={atCapacity}
          busy={busy}
          onOpenCreate={(status) => {
            setBox({ mode: 'create', initialStatus: status });
          }}
          onOpenEdit={() => {
            if (!myInputStatus) return;
            setBox({ mode: 'edit', initialStatus: myInputStatus });
          }}
        />
      )}

      <SpotsLeft event={event} />
      <Summary event={event} />
      {error ? (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      ) : null}

      <div className="mt-2">
        <RsvpGuestList event={event} canSeeInvited={canSeeInvited} />
      </div>

      {box ? (
        <RsvpBox
          key={box.mode + box.initialStatus}
          open
          mode={box.mode}
          initialStatus={box.initialStatus}
          initialHasPlusOne={hasPlusOne}
          allowPlusOnes={event.allowPlusOnes}
          onConfirm={(args) => void confirmRsvp(args)}
          onClose={() => {
            setBox(null);
          }}
        />
      ) : null}
    </section>
  );
}

function RsvpControls({
  myInputStatus,
  atCapacity,
  busy,
  onOpenCreate,
  onOpenEdit,
}: {
  myInputStatus: InputStatus | null;
  atCapacity: boolean;
  busy: boolean;
  onOpenCreate: (status: InputStatus) => void;
  onOpenEdit: () => void;
}) {
  if (myInputStatus) {
    return (
      <div className="flex items-center justify-center gap-3">
        <span className="text-foreground-secondary text-sm">{statusLine(myInputStatus)}</span>
        <Button variant="secondary" onClick={onOpenEdit} disabled={busy}>
          edit RSVP
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap justify-center gap-2">
      {PILLS.map((p) => {
        const waitlistAttending = p.status === RsvpStatus.Attending && atCapacity;
        return (
          <button
            key={p.status}
            type="button"
            disabled={busy}
            onClick={() => {
              onOpenCreate(p.status);
            }}
            className="border-border-strong text-foreground-secondary hover:bg-background inline-flex h-10 items-center rounded-full border px-4 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60"
          >
            {waitlistAttending ? 'join the waitlist' : p.label}
          </button>
        );
      })}
    </div>
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
