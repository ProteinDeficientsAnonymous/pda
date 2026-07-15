import { format, formatDistanceToNow } from 'date-fns';

import { JoinRequestStatus, type JoinRequestSummary, type RsvpBreakdown } from '@/api/join';
import { Button } from '@/components/ui/Button';
import { cn } from '@/utils/cn';
import { formatPhone } from '@/utils/formatPhone';

import { TentativeActions } from './JoinRequestTentativeSection';

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
  return (
    <article className="border-border bg-surface rounded-lg border p-4">
      <header className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-medium">{request.fullName}</h2>
          <p className="text-muted text-xs">
            {formatPhone(request.phoneNumber)} · {request.email} · submitted{' '}
            {format(new Date(request.submittedAt), 'MMM d, h:mm a')}
          </p>
          <RsvpBreakdownNote breakdown={request.rsvpBreakdown} />
        </div>
        <div className="flex flex-wrap items-center gap-1">
          {request.previouslyArchived ? (
            <span
              className="bg-warning-subtle text-warning rounded-full px-2 py-0.5 text-xs"
              title="this phone number belongs to a previously archived member — approving will restore their account"
            >
              previously archived
            </span>
          ) : null}
          <StatusBadge status={request.status} />
        </div>
      </header>

      {request.answers.length > 0 ? (
        <dl className="mt-2 flex flex-col gap-2">
          {request.answers.map((a) => (
            <div key={a.questionId}>
              <dt className="text-muted text-xs font-medium">{a.label}</dt>
              <dd className="text-foreground text-sm whitespace-pre-wrap">{a.answer}</dd>
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
        <TentativeActions
          request={request}
          busy={busy}
          onApprove={() => {
            onDecide('manually_approved');
          }}
        />
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
        </>
      )}
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

function DecisionAttribution({ request }: { request: JoinRequestSummary }) {
  if (request.status === JoinRequestStatus.APPROVED && request.approvedAt) {
    const who = request.approvedByName ?? 'an admin';
    return (
      <>
        <p className="text-muted mt-3 text-xs">
          approved by {who.toLowerCase()} on{' '}
          {format(new Date(request.approvedAt), 'MMM d, h:mm a').toLowerCase()}
        </p>
        <LoginStatus onboardedAt={request.onboardedAt} />
      </>
    );
  }
  if (request.status === JoinRequestStatus.REJECTED && request.rejectedAt) {
    const who = request.rejectedByName ?? 'an admin';
    return (
      <p className="text-muted mt-3 text-xs">
        rejected by {who.toLowerCase()} on{' '}
        {format(new Date(request.rejectedAt), 'MMM d, h:mm a').toLowerCase()}
      </p>
    );
  }
  return null;
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
};
