import { useMemo, useState } from 'react';
import { format } from 'date-fns';
import { isAxiosError } from 'axios';
import {
  useDecideJoinRequest,
  useJoinRequests,
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
        <p role="alert" className="mb-3 text-sm text-destructive">
          {error}
        </p>
      ) : null}

      {visible.length === 0 ? (
        <p className="text-sm text-muted">nothing here 🌿</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {visible.map((r) => (
            <li key={r.id}>
              <JoinRequestCard
                request={r}
                busy={decide.isPending}
                onDecide={(status) => {
                  void decideRequest(r, status);
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
}: {
  request: JoinRequestSummary;
  busy: boolean;
  onDecide: (status: 'approved' | 'rejected') => void;
}) {
  const isPending = request.status === 'pending';
  return (
    <article className="rounded-lg border border-border bg-surface p-4">
      <header className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-medium">{request.displayName}</h2>
          <p className="text-xs text-muted">
            {request.phoneNumber} · submitted{' '}
            {format(new Date(request.submittedAt), 'MMM d, h:mm a')}
          </p>
        </div>
        <StatusBadge status={request.status} />
      </header>

      {request.answers.length > 0 ? (
        <dl className="mt-2 flex flex-col gap-2">
          {request.answers.map((a) => (
            <div key={a.questionId}>
              <dt className="text-xs font-medium text-muted">{a.label}</dt>
              <dd className="text-sm whitespace-pre-wrap text-foreground">{a.answer}</dd>
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
            variant="ghost"
            onClick={() => {
              onDecide('rejected');
            }}
            disabled={busy}
          >
            reject
          </Button>
        </div>
      ) : null}
    </article>
  );
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
