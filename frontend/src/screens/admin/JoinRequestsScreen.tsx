import { useMemo, useState } from 'react';
import { format } from 'date-fns';
import { isAxiosError } from 'axios';
import {
  useDecideJoinRequest,
  useJoinRequests,
  useUnrejectJoinRequest,
  type JoinRequestStatus,
  type JoinRequestSummary,
} from '@/api/join';
import { Button } from '@/components/ui/Button';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { cn } from '@/utils/cn';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { ApprovalCredentialsDialog } from './ApprovalCredentialsDialog';

type Filter = 'all' | JoinRequestStatus;

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'all', label: 'all' },
  { value: 'pending', label: 'pending' },
  { value: 'approved', label: 'approved' },
  { value: 'rejected', label: 'rejected' },
];

export default function JoinRequestsScreen() {
  const { data = [], isPending, isError } = useJoinRequests();
  const decide = useDecideJoinRequest();
  const unreject = useUnrejectJoinRequest();

  const [filter, setFilter] = useState<Filter>('pending');
  const [error, setError] = useState<string | null>(null);
  const [credsFor, setCredsFor] = useState<{
    displayName: string;
    phoneNumber: string;
    magicLinkToken: string;
  } | null>(null);

  const visible = useMemo(() => {
    if (filter === 'all') return data;
    return data.filter((r) => r.status === filter);
  }, [data, filter]);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load join requests — try refreshing" />;

  async function decideRequest(request: JoinRequestSummary, status: 'approved' | 'rejected') {
    const name = request.displayName || request.phoneNumber;
    const message =
      status === 'approved'
        ? `approve ${name}? once you approve someone you can't un-approve them — are you sure?`
        : `reject ${name}? once you reject someone you can't un-reject them — are you sure?`;
    if (!window.confirm(message)) return;

    setError(null);
    try {
      const result = await decide.mutateAsync({ id: request.id, status });
      if (status === 'approved' && result.magicLinkToken) {
        setCredsFor({
          displayName: result.displayName,
          phoneNumber: result.phoneNumber,
          magicLinkToken: result.magicLinkToken,
        });
      }
    } catch (err) {
      setError(extractError(err));
    }
  }

  async function unrejectRequest(request: JoinRequestSummary) {
    const name = request.displayName || request.phoneNumber;
    if (!window.confirm(`un-reject ${name}? this will move them back to pending review.`)) return;

    setError(null);
    try {
      await unreject.mutateAsync(request.id);
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

      {error ? (
        <p role="alert" className="text-destructive mb-3 text-sm">
          {error}
        </p>
      ) : null}

      {visible.length === 0 ? (
        <p className="text-muted text-sm">nothing here 🌿</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {visible.map((r) => (
            <li key={r.id}>
              <JoinRequestCard
                request={r}
                busy={decide.isPending || unreject.isPending}
                onDecide={(status) => {
                  void decideRequest(r, status);
                }}
                onUnreject={() => {
                  void unrejectRequest(r);
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
          displayName={credsFor.displayName}
          phoneNumber={credsFor.phoneNumber}
          magicLinkToken={credsFor.magicLinkToken}
        />
      ) : null}
    </ContentContainer>
  );
}

function JoinRequestCard({
  request,
  busy,
  onDecide,
  onUnreject,
}: {
  request: JoinRequestSummary;
  busy: boolean;
  onDecide: (status: 'approved' | 'rejected') => void;
  onUnreject: () => void;
}) {
  const isPending = request.status === 'pending';
  const isRejected = request.status === 'rejected';
  return (
    <article className="border-border bg-surface rounded-lg border p-4">
      <header className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-medium">{request.displayName}</h2>
          <p className="text-muted text-xs">
            {request.phoneNumber} · submitted{' '}
            {format(new Date(request.submittedAt), 'MMM d, h:mm a')}
          </p>
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
              onDecide('approved');
            }}
            disabled={busy}
          >
            approve
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              onDecide('rejected');
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
        </>
      )}
    </article>
  );
}

function DecisionAttribution({ request }: { request: JoinRequestSummary }) {
  if (request.status === 'approved' && request.approvedAt) {
    const who = request.approvedByName ?? 'an admin';
    return (
      <p className="text-muted mt-3 text-xs">
        approved by {who.toLowerCase()} on{' '}
        {format(new Date(request.approvedAt), 'MMM d, h:mm a').toLowerCase()}
      </p>
    );
  }
  if (request.status === 'rejected' && request.rejectedAt) {
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

function StatusBadge({ status }: { status: JoinRequestStatus }) {
  const tone =
    status === 'approved'
      ? 'bg-success-subtle text-success'
      : status === 'rejected'
        ? 'bg-surface-raised text-foreground-secondary'
        : 'bg-warning-subtle text-warning';
  return <span className={cn('rounded-full px-2 py-0.5 text-xs', tone)}>{status}</span>;
}

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't complete that action — try again";
}
