import { useState } from 'react';
import { format } from 'date-fns';
import { isAxiosError } from 'axios';
import { Link } from 'react-router-dom';
import { useDecideFlag, useEventFlags, type FlagStatus, type EventFlag } from '@/api/eventFlags';
import { Button } from '@/components/ui/Button';
import { cn } from '@/utils/cn';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

const FILTERS: { value: FlagStatus | 'all'; label: string }[] = [
  { value: 'pending', label: 'pending' },
  { value: 'actioned', label: 'actioned' },
  { value: 'dismissed', label: 'dismissed' },
  { value: 'all', label: 'all' },
];

export default function FlaggedEventsScreen() {
  const [filter, setFilter] = useState<FlagStatus | 'all'>('pending');
  const { data = [], isPending, isError } = useEventFlags(filter === 'all' ? undefined : filter);
  const decide = useDecideFlag();
  const [error, setError] = useState<string | null>(null);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load flags — try refreshing" />;

  async function act(flag: EventFlag, status: 'dismissed' | 'actioned') {
    setError(null);
    try {
      await decide.mutateAsync({ id: flag.id, status });
    } catch (err) {
      setError(extractError(err));
    }
  }

  return (
    <ContentContainer>
      <h1 className="mb-6 text-2xl font-medium tracking-tight">flagged events</h1>

      <div role="tablist" aria-label="filter" className="mb-4 flex flex-wrap gap-1">
        {FILTERS.map((f) => {
          const active = filter === f.value;
          return (
            <button
              key={f.value}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => {
                setFilter(f.value);
              }}
              className={cn(
                'rounded-full px-3 py-1 text-xs transition-colors',
                active
                  ? 'bg-neutral-900 text-white'
                  : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200',
              )}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {error ? (
        <p role="alert" className="mb-3 text-sm text-red-600">
          {error}
        </p>
      ) : null}

      {data.length === 0 ? (
        <p className="text-sm text-neutral-500">nothing here 🌿</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {data.map((f) => (
            <li key={f.id}>
              <FlagRow
                flag={f}
                busy={decide.isPending}
                onDecide={(status) => {
                  void act(f, status);
                }}
              />
            </li>
          ))}
        </ul>
      )}
    </ContentContainer>
  );
}

function FlagRow({
  flag,
  busy,
  onDecide,
}: {
  flag: EventFlag;
  busy: boolean;
  onDecide: (status: 'dismissed' | 'actioned') => void;
}) {
  const isPending = flag.status === 'pending';
  return (
    <article className="rounded-lg border border-neutral-200 bg-white p-4">
      <header className="mb-2 flex flex-wrap items-start justify-between gap-2">
        <div>
          <Link
            to={`/events/${flag.eventId}`}
            className="text-base font-medium text-neutral-900 underline"
          >
            {flag.eventTitle}
          </Link>
          <p className="text-xs text-neutral-500">
            flagged by {flag.flaggedByName} · {format(new Date(flag.createdAt), 'MMM d, h:mm a')}
          </p>
        </div>
        <StatusBadge status={flag.status} />
      </header>
      <p className="text-sm whitespace-pre-wrap text-neutral-800">{flag.reason}</p>
      {isPending ? (
        <div className="mt-4 flex gap-2">
          <Button
            onClick={() => {
              onDecide('actioned');
            }}
            disabled={busy}
          >
            mark actioned
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              onDecide('dismissed');
            }}
            disabled={busy}
          >
            dismiss
          </Button>
        </div>
      ) : null}
    </article>
  );
}

function StatusBadge({ status }: { status: FlagStatus }) {
  const tone =
    status === 'actioned'
      ? 'bg-green-100 text-green-800'
      : status === 'dismissed'
        ? 'bg-neutral-200 text-neutral-700'
        : 'bg-amber-100 text-amber-800';
  return <span className={cn('rounded-full px-2 py-0.5 text-xs', tone)}>{status}</span>;
}

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't complete that action — try again";
}
