import { format, formatDistanceToNow } from 'date-fns';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { JoinRequestStatus, type JoinRequestSummary, type RsvpBreakdown } from '@/api/join';
import { rejectionReasonText } from '@/api/rejectionEmail';
import { Button } from '@/components/ui/Button';
import { cn } from '@/utils/cn';
import { formatPhone } from '@/utils/formatPhone';

import { AttendedEventsNote } from './AttendedEventsNote';
import { PreviousArchiveNote, PreviousRejectionNote } from './JoinRequestPreviousRejection';
import { TentativeActions } from './JoinRequestTentativeSection';
import { JoinRequestWhatsappToggle } from './JoinRequestWhatsappToggle';
import { SendMessageDialog } from './SendMessageDialog';

export type Decision =
  | typeof JoinRequestStatus.APPROVED
  | typeof JoinRequestStatus.TENTATIVE
  | typeof JoinRequestStatus.REJECTED
  | 'manually_approved';

export function JoinRequestCard({
  request,
  busy,
  onDecide,
  onUnreject,
  onResend,
}: {
  request: JoinRequestSummary;
  busy: boolean;
  onDecide: (status: Decision) => void;
  onUnreject: () => void;
  onResend: () => void;
}) {
  const isPending = request.status === JoinRequestStatus.PENDING;
  const isTentative = request.status === JoinRequestStatus.TENTATIVE;
  const isRejected = request.status === JoinRequestStatus.REJECTED;
  const canResend = request.status === JoinRequestStatus.APPROVED && request.onboardedAt === null;
  const [messageOpen, setMessageOpen] = useState(false);
  return (
    <article className="border-border bg-surface rounded-lg border p-4">
      <header className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-medium">{request.fullName}</h2>
          <p className="text-muted text-xs">
            {formatPhone(request.phoneNumber)} · {request.email} · submitted{' '}
            {format(new Date(request.submittedAt), 'MMM d, h:mm a').toLowerCase()}
          </p>
          <RsvpBreakdownNote breakdown={request.rsvpBreakdown} />
          <AttendedEventsNote events={request.attendedEvents} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            className="h-8 px-3 text-xs"
            onClick={() => {
              setMessageOpen(true);
            }}
          >
            send message
          </Button>
          {request.previouslyArchived ? (
            <span
              className="bg-warning-subtle text-warning rounded-full px-2 py-0.5 text-xs"
              title="this phone number belongs to a previously archived account — approving or tentatively approving restores it"
            >
              previously archived
            </span>
          ) : null}
          {request.previouslyRejected ? (
            <span
              className="bg-warning-subtle text-warning rounded-full px-2 py-0.5 text-xs"
              title="an earlier request from this number was rejected"
            >
              previously rejected
            </span>
          ) : null}
          <StatusBadge status={request.status} />
        </div>
      </header>
      <PreviousArchiveNote archive={request.previousArchive} />
      <PreviousRejectionNote rejection={request.previousRejection} />

      {request.answers.length > 0 ? (
        <dl className="mt-2 flex flex-col gap-2">
          {request.answers.map((a) => (
            <div key={a.questionId}>
              <dt className="text-muted text-xs font-medium">{a.label}</dt>
              <dd className="text-foreground text-sm whitespace-pre-wrap">
                {Array.isArray(a.answer) ? a.answer.join('\n') : a.answer}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}

      {isPending ? (
        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            onClick={() => {
              onDecide(JoinRequestStatus.APPROVED);
            }}
            disabled={busy}
          >
            approve
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              onDecide(JoinRequestStatus.TENTATIVE);
            }}
            disabled={busy}
          >
            tentatively approve
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              onDecide(JoinRequestStatus.REJECTED);
            }}
            disabled={busy}
          >
            reject
          </Button>
        </div>
      ) : isTentative ? (
        <>
          <TentativeAttribution request={request} />
          <LoginStatus onboardedAt={request.onboardedAt} />
          <TentativeActions
            request={request}
            busy={busy}
            onApprove={() => {
              onDecide('manually_approved');
            }}
          />
        </>
      ) : (
        <>
          <DecisionAttribution request={request} />
          {isRejected ? (
            <div className="mt-3">
              <Button variant="secondary" onClick={onUnreject} disabled={busy}>
                un-reject
              </Button>
            </div>
          ) : null}
          {canResend ? (
            <div className="mt-3">
              <Button variant="secondary" onClick={onResend} disabled={busy}>
                re-send welcome
              </Button>
            </div>
          ) : null}
          {request.status === JoinRequestStatus.APPROVED && request.userId ? (
            <JoinRequestWhatsappToggle
              userId={request.userId}
              checked={request.userHasJoinedWhatsapp}
            />
          ) : null}
        </>
      )}

      <SendMessageDialog
        open={messageOpen}
        onClose={() => {
          setMessageOpen(false);
        }}
        fullName={request.fullName}
        phoneNumber={request.phoneNumber}
      />
    </article>
  );
}

function attendedLine(count: number, eventType: string): string {
  const noun = count === 1 ? 'event' : 'events';
  return `attended ${String(count)} ${eventType} ${noun}`;
}

function upcomingLine(count: number, eventType: string): string {
  const noun = count === 1 ? 'event' : 'events';
  return `rsvp'd for ${String(count)} upcoming ${eventType} ${noun}`;
}

function RsvpBreakdownNote({ breakdown }: { breakdown: RsvpBreakdown }) {
  const lines = [
    {
      count: breakdown.attendedOfficial,
      text: attendedLine(breakdown.attendedOfficial, 'official'),
    },
    { count: breakdown.attendedClub, text: attendedLine(breakdown.attendedClub, 'club') },
    {
      count: breakdown.upcomingOfficial,
      text: upcomingLine(breakdown.upcomingOfficial, 'official'),
    },
    { count: breakdown.upcomingClub, text: upcomingLine(breakdown.upcomingClub, 'club') },
  ].filter((line) => line.count > 0);
  if (lines.length === 0) return null;
  return (
    <div className="text-muted mt-1 text-xs">
      {lines.map((line) => (
        <p key={line.text}>{line.text}</p>
      ))}
    </div>
  );
}

function stampText(at: string): string {
  return format(new Date(at), 'MMM d, h:mm a').toLowerCase();
}

function changedBy(request: JoinRequestSummary): string {
  return (request.statusChangedByName ?? 'an admin').toLowerCase();
}

function TentativeAttribution({ request }: { request: JoinRequestSummary }) {
  const at = request.statusChangedAt;
  if (!at) return null;
  return (
    <p className="text-muted mt-3 text-xs">
      tentatively approved by {changedBy(request)} on {stampText(at)}
    </p>
  );
}

function DecisionAttribution({ request }: { request: JoinRequestSummary }) {
  const at = request.statusChangedAt;
  if (!at) return null;
  if (request.status === JoinRequestStatus.APPROVED) {
    if (request.approvedViaEventId) {
      return (
        <>
          <p className="text-muted mt-3 text-xs">
            auto approved after joining{' '}
            <Link to={`/events/${request.approvedViaEventId}`} className="hover:underline">
              {(request.approvedViaEventTitle ?? 'an event').toLowerCase()}
            </Link>{' '}
            on {stampText(at)}
          </p>
          <LoginStatus onboardedAt={request.onboardedAt} />
        </>
      );
    }
    return (
      <>
        <p className="text-muted mt-3 text-xs">
          approved by {changedBy(request)} on {stampText(at)}
        </p>
        <LoginStatus onboardedAt={request.onboardedAt} />
      </>
    );
  }
  if (request.status === JoinRequestStatus.REJECTED) {
    return (
      <>
        <p className="text-muted mt-3 text-xs">
          rejected by {changedBy(request)} on {stampText(at)}
        </p>
        <RejectionReasonLine request={request} />
      </>
    );
  }
  if (request.status === JoinRequestStatus.CLOSED) {
    return (
      <p className="text-muted mt-3 text-xs">
        closed when {changedBy(request)} archived them on {stampText(at)}
      </p>
    );
  }
  return null;
}

function RejectionReasonLine({ request }: { request: JoinRequestSummary }) {
  const text = rejectionReasonText(request.rejectionReason, request.rejectionNote);
  if (!text) return null;
  return <p className="text-muted mt-1 text-xs whitespace-pre-wrap">reason: {text}</p>;
}

function LoginStatus({ onboardedAt }: { onboardedAt: string | null }) {
  if (!onboardedAt) {
    return <p className="text-muted mt-1 text-xs">hasn&rsquo;t logged in yet</p>;
  }
  const relative = formatDistanceToNow(new Date(onboardedAt), { addSuffix: true }).toLowerCase();
  return <p className="text-muted mt-1 text-xs">logged in {relative}</p>;
}

function StatusBadge({ status }: { status: JoinRequestStatus }) {
  const tone = STATUS_TONES[status];
  return <span className={cn('rounded-full px-2 py-0.5 text-xs', tone)}>{status}</span>;
}

const STATUS_TONES: Record<JoinRequestStatus, string> = {
  [JoinRequestStatus.PENDING]: 'bg-warning-subtle text-warning',
  [JoinRequestStatus.TENTATIVE]: 'bg-highlight-subtle text-highlight',
  [JoinRequestStatus.APPROVED]: 'bg-success-subtle text-success',
  [JoinRequestStatus.REJECTED]: 'bg-surface-raised text-foreground-secondary',
  [JoinRequestStatus.CLOSED]: 'bg-surface-raised text-foreground-secondary',
};
