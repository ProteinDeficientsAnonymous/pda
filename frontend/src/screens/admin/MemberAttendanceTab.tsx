import { format } from 'date-fns';
import { useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  type MemberAttendanceRow,
  useMemberAttendanceAnalytics,
} from '@/api/memberAttendanceAnalytics';
import { useUpdateUser } from '@/api/users';
import { useAuthStore } from '@/auth/store';
import { useConfirm } from '@/components/ui/useConfirm';
import { hasPermission, Permission } from '@/models/permissions';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { cn } from '@/utils/cn';
import { formatPhone } from '@/utils/formatPhone';

type Filter = 'all' | 'at-risk';

export function MemberAttendanceTab() {
  const { data = [], isPending, isError } = useMemberAttendanceAnalytics();
  const [filter, setFilter] = useState<Filter>('all');

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load member attendance — try refreshing" />;

  const visible = filter === 'at-risk' ? data.filter((m) => m.isPauseCandidate) : data;

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <FilterButton
          active={filter === 'all'}
          onClick={() => {
            setFilter('all');
          }}
        >
          all members
        </FilterButton>
        <FilterButton
          active={filter === 'at-risk'}
          onClick={() => {
            setFilter('at-risk');
          }}
        >
          at risk
        </FilterButton>
      </div>

      {visible.length === 0 ? (
        <p className="text-muted text-sm">nothing here 🌿</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {visible.map((row) => (
            <li key={row.userId}>
              <MemberAttendanceRowCard row={row} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function FilterButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-full px-3 py-1 text-xs font-medium transition-colors',
        active
          ? 'bg-brand-600 text-brand-on'
          : 'bg-surface-dim text-foreground-secondary hover:bg-surface-raised',
      )}
    >
      {children}
    </button>
  );
}

function lastQualifyingLine(row: MemberAttendanceRow): string {
  if (!row.lastQualifyingAt) return 'never attended a qualifying event';
  const date = format(row.lastQualifyingAt, 'MMM d, yyyy').toLowerCase();
  const months = row.monthsSinceLastQualifying;
  const ago = months === null || months === 0 ? 'this month' : `${String(months)}mo ago`;
  return `last qualifying: ${date} (${ago})`;
}

function MemberAttendanceRowCard({ row }: { row: MemberAttendanceRow }) {
  const currentUser = useAuthStore((s) => s.user);
  const canPause = hasPermission(currentUser, Permission.ManageUsers);

  return (
    <article className="border-border bg-surface rounded-lg border p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-foreground truncate text-sm font-medium">
            {row.fullName.toLowerCase()}
          </p>
          <p className="text-foreground-tertiary text-xs">{formatPhone(row.phoneNumber)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          {row.isPaused ? <Badge tone="neutral">paused</Badge> : null}
          {row.isPauseCandidate ? (
            <Badge tone="warning">pause candidate</Badge>
          ) : row.compliant ? (
            <Badge tone="success">compliant</Badge>
          ) : (
            <Badge tone="neutral">not yet compliant</Badge>
          )}
        </div>
      </div>

      <p className="text-muted mt-2 text-xs">{lastQualifyingLine(row)}</p>

      <div className="mt-2 flex flex-wrap gap-1 text-xs">
        <Stat label="qualifying (12mo)" value={row.qualifyingCount12mo} />
        <Stat label="community events" value={row.communityCount} />
        <Stat label="no-shows" value={row.noShowCount} />
        <Stat label="cancels" value={row.cancelCount} />
      </div>

      {canPause && !row.isPaused ? <PauseButton row={row} /> : null}
    </article>
  );
}

function PauseButton({ row }: { row: MemberAttendanceRow }) {
  const update = useUpdateUser(row.userId);
  const { confirm, element } = useConfirm();

  async function onPause() {
    const ok = await confirm({
      title: 'pause this member?',
      message: `${row.fullName.toLowerCase()} won't be able to log in until unpaused — do this from the members screen.`,
      confirmLabel: 'pause',
      destructive: true,
    });
    if (!ok) return;
    try {
      await update.mutateAsync({ isPaused: true });
      toast.success('member paused ✓');
    } catch (err) {
      toast.error(extractApiErrorOr(err, "couldn't pause member — try again"));
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => void onPause()}
        disabled={update.isPending}
        className="text-warning mt-3 text-xs font-medium hover:underline disabled:opacity-50"
      >
        pause member
      </button>
      {element}
    </>
  );
}

const BADGE_TONES = {
  success: 'bg-success-subtle text-success',
  warning: 'bg-warning-subtle text-warning',
  neutral: 'bg-surface-dim text-foreground-secondary',
} as const;

function Badge({ tone, children }: { tone: keyof typeof BADGE_TONES; children: string }) {
  return (
    <span className={cn('rounded-full px-2 py-0.5 text-xs', BADGE_TONES[tone])}>{children}</span>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <span className="bg-surface-dim text-foreground-secondary rounded-full px-2.5 py-0.5">
      <span className="text-foreground font-medium">{value}</span> {label}
    </span>
  );
}
