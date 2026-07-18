import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useCancelPublicMyRsvp, useUpdatePublicMyRsvp } from '@/api/publicRsvp';
import { useRemoveRsvp, useSetRsvp } from '@/api/rsvp';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { RsvpStatusPicker } from '@/components/ui/RsvpStatusPicker';
import {
  type Event,
  isRsvpInputStatus,
  type RsvpInputStatus,
  RsvpServerStatus,
  RsvpStatus,
  spotsLeft,
} from '@/models/event';

import { RsvpBox } from './RsvpBox';
import { RsvpGuestList } from './RsvpGuestList';

interface Props {
  event: Event;
  canSeeInvited: boolean;
  token?: string;
}

const STATUS_LINES: Record<RsvpInputStatus, string> = {
  [RsvpStatus.Attending]: "you're going",
  [RsvpStatus.Maybe]: "you're a maybe",
  [RsvpStatus.CantGo]: "you can't go",
};

interface BoxState {
  mode: 'create' | 'edit';
  initialStatus: RsvpInputStatus;
}

export function RsvpSection({ event, canSeeInvited, token }: Props) {
  const setRsvp = useSetRsvp();
  const removeRsvp = useRemoveRsvp();
  const updatePublicRsvp = useUpdatePublicMyRsvp(token ?? '');
  const cancelPublicRsvp = useCancelPublicMyRsvp(token ?? '');
  const authUserId = useAuthStore((s) => s.user?.id);
  // A token holder has no useAuthStore session (not logged in) — their
  // identity comes from the backend-resolved viewer instead (issue #854).
  const myUserId = token ? event.viewerUserId : authUserId;
  const [error, setError] = useState<string | null>(null);
  const [box, setBox] = useState<BoxState | null>(null);

  const myRsvp = event.myRsvp;
  const onWaitlist = myRsvp === RsvpServerStatus.Waitlisted;
  const myInputStatus = isRsvpInputStatus(myRsvp) ? myRsvp : null;
  // Match by user id, not status — multiple guests share the same status,
  // so a status match returns some other attendee's record and the +1
  // toggle reflects the wrong user (issue #368).
  const myGuest = event.guests.find((g) => g.userId === myUserId);
  const hasPlusOne = myGuest?.hasPlusOne ?? false;
  const atCapacity = spotsLeft(event) === 0;

  async function confirmRsvp(args: {
    status: RsvpInputStatus;
    comment?: string;
    hasPlusOne: boolean;
  }) {
    setError(null);
    try {
      if (token) {
        await updatePublicRsvp.mutateAsync({
          eventId: event.id,
          status: args.status,
          hasPlusOne: args.hasPlusOne,
          ...(args.comment !== undefined ? { comment: args.comment } : {}),
        });
      } else {
        await setRsvp.mutateAsync({
          eventId: event.id,
          status: args.status,
          hasPlusOne: args.hasPlusOne,
          ...(args.comment === undefined ? {} : { comment: args.comment }),
        });
      }
      setBox(null);
    } catch (err) {
      setError(extractError(err));
    }
  }

  async function leaveWaitlist() {
    setError(null);
    try {
      if (token) {
        await cancelPublicRsvp.mutateAsync(event.id);
      } else {
        await removeRsvp.mutateAsync(event.id);
      }
    } catch (err) {
      setError(extractError(err));
    }
  }

  async function removeMyRsvp() {
    setError(null);
    try {
      if (token) {
        await cancelPublicRsvp.mutateAsync(event.id);
      } else {
        await removeRsvp.mutateAsync(event.id);
      }
      setBox(null);
    } catch (err) {
      setError(extractError(err));
    }
  }

  const busy =
    setRsvp.isPending ||
    removeRsvp.isPending ||
    updatePublicRsvp.isPending ||
    cancelPublicRsvp.isPending;

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
          allowComment={Boolean(token) || box.mode === 'create'}
          busy={busy}
          onConfirm={(args) => void confirmRsvp(args)}
          onRemove={box.mode === 'edit' ? () => void removeMyRsvp() : undefined}
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
  myInputStatus: RsvpInputStatus | null;
  atCapacity: boolean;
  busy: boolean;
  onOpenCreate: (status: RsvpInputStatus) => void;
  onOpenEdit: () => void;
}) {
  if (myInputStatus) {
    return (
      <div className="flex items-center justify-center gap-3">
        <span className="text-foreground-secondary text-sm">{STATUS_LINES[myInputStatus]}</span>
        <Button variant="secondary" onClick={onOpenEdit} disabled={busy}>
          edit rsvp
        </Button>
      </div>
    );
  }

  return (
    <RsvpStatusPicker
      value={null}
      disabled={busy}
      onSelect={onOpenCreate}
      labelFor={(status, defaultLabel) =>
        status === RsvpStatus.Attending && atCapacity ? 'join the waitlist' : defaultLabel
      }
    />
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
