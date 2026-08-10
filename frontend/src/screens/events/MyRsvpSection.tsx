import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useCancelPublicMyRsvp, useUpdatePublicMyRsvp } from '@/api/publicRsvp';
import { useRemoveRsvp, useSetRsvp } from '@/api/rsvp';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import {
  type Event,
  isRsvpInputStatus,
  type RsvpInputStatus,
  RsvpServerStatus,
  RsvpStatus,
  spotsLeft,
} from '@/models/event';

import { RsvpBox } from './RsvpBox';
import type { RsvpAnswerValue } from './rsvpQuestions';

interface Props {
  event: Event;
  token?: string;
  locked?: boolean;
}

const STATUS_LINES: Record<RsvpInputStatus, string> = {
  [RsvpStatus.Attending]: "you're going",
  [RsvpStatus.Maybe]: "you're a maybe",
  [RsvpStatus.CantGo]: "you can't go",
};

const STATUS_BADGE_LABELS: Record<RsvpInputStatus, string> = {
  [RsvpStatus.Attending]: "i'm going",
  [RsvpStatus.Maybe]: 'maybe',
  [RsvpStatus.CantGo]: "i can't go",
};

const PAST_STATUS_LABELS: Record<RsvpInputStatus, string> = {
  [RsvpStatus.Attending]: 'you went',
  [RsvpStatus.Maybe]: 'you were a maybe',
  [RsvpStatus.CantGo]: "you couldn't go",
};

interface BoxState {
  mode: 'create' | 'edit';
  initialStatus: RsvpInputStatus;
}

export function MyRsvpSection({ event, token, locked = false }: Props) {
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
    paidConfirmed?: boolean;
    questionnaireResponses: Record<string, RsvpAnswerValue>;
  }) {
    setError(null);
    try {
      if (token) {
        await updatePublicRsvp.mutateAsync({
          eventId: event.id,
          status: args.status,
          hasPlusOne: args.hasPlusOne,
          questionnaireResponses: args.questionnaireResponses,
          ...(args.comment !== undefined ? { comment: args.comment } : {}),
          ...(args.paidConfirmed ? { paidConfirmed: true } : {}),
        });
      } else {
        await setRsvp.mutateAsync({
          eventId: event.id,
          status: args.status,
          hasPlusOne: args.hasPlusOne,
          questionnaireResponses: args.questionnaireResponses,
          ...(args.comment === undefined ? {} : { comment: args.comment }),
          ...(args.paidConfirmed ? { paidConfirmed: true } : {}),
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
      {!locked && onWaitlist ? (
        <WaitlistView onLeave={() => void leaveWaitlist()} busy={busy} />
      ) : (
        <RsvpControls
          myInputStatus={myInputStatus}
          atCapacity={atCapacity}
          busy={busy}
          locked={locked}
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
      {error ? (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      ) : null}

      {box ? (
        <RsvpBox
          key={box.mode + box.initialStatus}
          open
          mode={box.mode}
          event={event}
          initialStatus={box.initialStatus}
          initialHasPlusOne={hasPlusOne}
          allowPlusOnes={event.allowPlusOnes}
          allowComment={Boolean(token) || box.mode === 'create'}
          atCapacity={atCapacity}
          busy={busy}
          questions={event.rsvpQuestions}
          initialAnswers={Object.fromEntries(
            Object.entries(event.myQuestionnaireResponses).map(([id, snap]) => [id, snap.answer]),
          )}
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

const RSVP_PILL_CLASSES =
  'mx-auto inline-flex h-12 min-w-28 items-center justify-center rounded-full px-5 text-base font-medium bg-brand-600 text-brand-on';

function RsvpControls({
  myInputStatus,
  atCapacity,
  busy,
  locked,
  onOpenCreate,
  onOpenEdit,
}: {
  myInputStatus: RsvpInputStatus | null;
  atCapacity: boolean;
  busy: boolean;
  locked?: boolean;
  onOpenCreate: (status: RsvpInputStatus) => void;
  onOpenEdit: () => void;
}) {
  if (locked) {
    if (!myInputStatus) return null;
    return (
      <span className={RSVP_PILL_CLASSES}>
        <span role="status">{PAST_STATUS_LABELS[myInputStatus]}</span>
      </span>
    );
  }

  if (!myInputStatus) {
    return (
      <button
        type="button"
        onClick={() => {
          onOpenCreate(RsvpStatus.Attending);
        }}
        disabled={busy}
        className={`${RSVP_PILL_CLASSES} hover:bg-brand-700 transition-colors disabled:opacity-60`}
      >
        {atCapacity ? 'join the waitlist' : 'rsvp'}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={onOpenEdit}
      disabled={busy}
      aria-label={`${STATUS_LINES[myInputStatus]} — edit rsvp`}
      className={`${RSVP_PILL_CLASSES} hover:bg-brand-700 transition-colors disabled:opacity-60`}
    >
      <span role="status">{STATUS_BADGE_LABELS[myInputStatus]}</span>
    </button>
  );
}

function WaitlistView({ onLeave, busy }: { onLeave: () => void; busy: boolean }) {
  return (
    <div className="bg-warning-subtle flex items-center justify-between gap-3 rounded-lg px-4 py-3">
      <span role="status" className="text-warning text-sm font-medium">
        you're on the waitlist
      </span>
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

function extractError(err: unknown): string {
  return extractApiErrorOr(err, "couldn't update your rsvp — try again");
}
