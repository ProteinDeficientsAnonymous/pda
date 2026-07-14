import { format, formatDistanceToNow } from 'date-fns';
import { useMemo, useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  JoinRequestStatus,
  type JoinRequestSummary,
  type RsvpBreakdown,
  useDecideJoinRequest,
  useJoinRequests,
  useResendMagicLink,
  useUnrejectJoinRequest,
} from '@/api/join';
import { Button } from '@/components/ui/Button';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { TextField } from '@/components/ui/TextField';
import { useConfirm } from '@/components/ui/useConfirm';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { cn } from '@/utils/cn';
import { formatPhone } from '@/utils/formatPhone';

import { ApprovalCredentialsDialog } from './ApprovalCredentialsDialog';

const Filter = {
  ALL: 'all',
  ...JoinRequestStatus,
} as const;
type Filter = (typeof Filter)[keyof typeof Filter];

type Decision = typeof JoinRequestStatus.APPROVED | typeof JoinRequestStatus.REJECTED;

const FILTERS: { value: Filter; label: string }[] = [
  { value: Filter.ALL, label: 'all' },
  { value: Filter.PENDING, label: 'pending' },
  { value: Filter.APPROVED, label: 'approved' },
  { value: Filter.REJECTED, label: 'rejected' },
];

export default function JoinRequestsScreen() {
  const { data = [], isPending, isError } = useJoinRequests();
  const decide = useDecideJoinRequest();
  const unreject = useUnrejectJoinRequest();
  const resend = useResendMagicLink();
  const { confirm, element: confirmElement } = useConfirm();

  const [filter, setFilter] = useState<Filter>(Filter.PENDING);
  const [query, setQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [credsFor, setCredsFor] = useState<{
    fullName: string;
    firstName: string;
    phoneNumber: string;
    magicLinkToken: string;
  } | null>(null);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = data.filter(
      (r) => (filter === Filter.ALL || r.status === filter) && matchesQuery(r, q),
    );
    return [...rows].sort((a, b) => sortKey(b) - sortKey(a));
  }, [data, filter, query]);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load join requests — try refreshing" />;

  async function decideRequest(request: JoinRequestSummary, status: Decision) {
    const name = request.fullName || formatPhone(request.phoneNumber);
    const isApprove = status === JoinRequestStatus.APPROVED;
    const message = isApprove
      ? `approve ${name}? once you approve someone you can't un-approve them — are you sure?`
      : `reject ${name}? once you reject someone you can't un-reject them — are you sure?`;
    const ok = await confirm({
      title: isApprove ? 'approve request' : 'reject request',
      message,
      confirmLabel: isApprove ? 'approve' : 'reject',
      destructive: !isApprove,
    });
    if (!ok) return;

    setError(null);
    try {
      const result = await decide.mutateAsync({ id: request.id, status });
      if (isApprove && result.magicLinkToken) {
        setCredsFor({
          fullName: result.fullName,
          firstName: result.firstName,
          phoneNumber: result.phoneNumber,
          magicLinkToken: result.magicLinkToken,
        });
      }
    } catch (err) {
      setError(extractError(err));
    }
  }

  async function unrejectRequest(request: JoinRequestSummary) {
    const name = request.fullName || formatPhone(request.phoneNumber);
    const ok = await confirm({
      title: 'un-reject request',
      message: `un-reject ${name}? this will move them back to pending review.`,
      confirmLabel: 'un-reject',
    });
    if (!ok) return;

    setError(null);
    try {
      await unreject.mutateAsync(request.id);
    } catch (err) {
      setError(extractError(err));
    }
  }

  async function resendWelcome(request: JoinRequestSummary) {
    const name = request.fullName || formatPhone(request.phoneNumber);
    const ok = await confirm({
      title: 're-send welcome',
      message: `re-send welcome to ${name}? this generates a fresh login link and invalidates any earlier link you sent them.`,
      confirmLabel: 're-send',
    });
    if (!ok) return;

    setError(null);
    try {
      const result = await resend.mutateAsync(request.id);
      if (result.magicLinkToken) {
        setCredsFor({
          fullName: result.fullName,
          firstName: result.firstName,
          phoneNumber: result.phoneNumber,
          magicLinkToken: result.magicLinkToken,
        });
      }
    } catch (err) {
      setError(extractError(err));
    }
  }

  return (
    <ContentContainer>
      <h1 className="mb-6 text-2xl font-medium tracking-tight">join requests</h1>

      <div className="mb-4 flex justify-center">
        <SegmentedControl
          name="join-filter"
          ariaLabel="filter"
          options={FILTERS}
          value={filter}
          onChange={setFilter}
        />
      </div>

      <div className="mb-4">
        <TextField
          label="search"
          placeholder="name, phone, or email"
          value={query}
          maxLength={100}
          onChange={(e) => {
            setQuery(e.target.value);
          }}
        />
      </div>

      <SortHint filter={filter} hasRows={visible.length > 0} />

      {error ? (
        <p role="alert" className="text-destructive mb-3 text-sm">
          {error}
        </p>
      ) : null}

      {visible.length === 0 ? (
        <p className="text-muted text-sm">
          {query.trim() ? 'nothing matches — try a different search' : 'nothing here 🌿'}
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {visible.map((r) => (
            <li key={r.id}>
              <JoinRequestCard
                request={r}
                busy={decide.isPending || unreject.isPending || resend.isPending}
                onDecide={(status) => {
                  void decideRequest(r, status);
                }}
                onUnreject={() => {
                  void unrejectRequest(r);
                }}
                onResend={() => {
                  void resendWelcome(r);
                }}
              />
            </li>
          ))}
        </ul>
      )}

      {credsFor ? (
        <ApprovalCredentialsDialog
          open
          onClose={() => {
            setCredsFor(null);
          }}
          fullName={credsFor.fullName}
          firstName={credsFor.firstName}
          phoneNumber={credsFor.phoneNumber}
          magicLinkToken={credsFor.magicLinkToken}
        />
      ) : null}
      {confirmElement}
    </ContentContainer>
  );
}

function JoinRequestCard({
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
  const isRejected = request.status === JoinRequestStatus.REJECTED;
  const canResend = request.status === JoinRequestStatus.APPROVED && request.onboardedAt === null;
  return (
    <article className="border-border bg-surface rounded-lg border p-4">
      <header className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-medium">{request.fullName}</h2>
          <p className="text-muted text-xs">
            {formatPhone(request.phoneNumber)} · submitted{' '}
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
        <div className="mt-4 flex gap-2">
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
              onDecide(JoinRequestStatus.REJECTED);
            }}
            disabled={busy}
          >
            reject
          </Button>
        </div>
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
  [JoinRequestStatus.APPROVED]: 'bg-success-subtle text-success',
  [JoinRequestStatus.REJECTED]: 'bg-surface-raised text-foreground-secondary',
};

function SortHint({ filter, hasRows }: { filter: Filter; hasRows: boolean }) {
  if (filter === Filter.APPROVED) {
    return (
      <p className="text-muted mb-3 text-xs">
        sorted newest first — approved members show here until 3 days after their first login, then
        this tab clears them out automatically
      </p>
    );
  }
  if (!hasRows) return null;
  return <p className="text-muted mb-3 text-xs">sorted newest first</p>;
}

function sortKey(request: JoinRequestSummary): number {
  const stamp = request.approvedAt ?? request.rejectedAt ?? request.submittedAt;
  return new Date(stamp).getTime();
}

function matchesQuery(request: JoinRequestSummary, q: string): boolean {
  if (!q) return true;
  return (
    request.fullName.toLowerCase().includes(q) ||
    request.phoneNumber.toLowerCase().includes(q) ||
    request.email.toLowerCase().includes(q)
  );
}

function extractError(err: unknown): string {
  return extractApiErrorOr(err, "couldn't complete that action — try again");
}
