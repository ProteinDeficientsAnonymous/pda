import { format } from 'date-fns';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { type EventAttendanceRow, useAttendanceReport } from '@/api/attendanceReport';
import { useFlag } from '@/api/featureFlags';
import { Feature } from '@/models/featureFlags';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { cn } from '@/utils/cn';

import { MemberAttendanceTab } from './MemberAttendanceTab';

type Tab = 'events' | 'members';

export default function AttendanceReportScreen() {
  const membersTabEnabled = useFlag(Feature.AdminAttendanceAnalytics);
  const [tab, setTab] = useState<Tab>('events');

  return (
    <ContentContainer>
      <header className="mb-4">
        <h1 className="mb-1 text-2xl font-medium tracking-tight">attendance</h1>
        <p className="text-muted text-sm">who actually showed up, per event and per member</p>
      </header>

      {membersTabEnabled ? (
        <div
          role="tablist"
          aria-label="attendance view"
          className="border-border-strong bg-surface mb-4 flex w-full max-w-xs rounded-full border p-1"
        >
          <TabButton
            active={tab === 'events'}
            onClick={() => {
              setTab('events');
            }}
          >
            events
          </TabButton>
          <TabButton
            active={tab === 'members'}
            onClick={() => {
              setTab('members');
            }}
          >
            members
          </TabButton>
        </div>
      ) : null}

      {tab === 'members' && membersTabEnabled ? <MemberAttendanceTab /> : <EventsTab />}
    </ContentContainer>
  );
}

function TabButton({
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
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        'flex-1 rounded-full px-3 py-1 text-sm transition-colors',
        active ? 'bg-brand-600 text-brand-on' : 'text-foreground-secondary hover:bg-surface-dim',
      )}
    >
      {children}
    </button>
  );
}

function EventsTab() {
  const { data = [], isPending, isError } = useAttendanceReport();
  // The per-event report at /events/:id/report is behind its own flag; only
  // link rows there when it's on, otherwise the row dead-links to /calendar.
  const reportEnabled = useFlag(Feature.HostAttendanceReport);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load attendance — try refreshing" />;

  return data.length === 0 ? (
    <p className="text-muted text-sm">no attendance marked yet 🌿</p>
  ) : (
    <ul className="flex flex-col gap-2">
      {data.map((row) => (
        <li key={row.eventId}>
          <AttendanceRow row={row} linkable={reportEnabled} />
        </li>
      ))}
    </ul>
  );
}

function AttendanceRow({ row, linkable }: { row: EventAttendanceRow; linkable: boolean }) {
  const content = (
    <>
      <div className="min-w-0 flex-1">
        <p className="text-foreground truncate text-sm font-medium">{row.title.toLowerCase()}</p>
        <p className="text-foreground-tertiary truncate text-xs">
          {row.startDatetime
            ? format(row.startDatetime, 'EEE MMM d, yyyy').toLowerCase()
            : 'date tbd'}
        </p>
      </div>
      <div className="flex shrink-0 flex-wrap justify-end gap-1 text-xs">
        <Stat label="attended" value={row.attendedCount} />
        <Stat label="no-show" value={row.noShowCount} />
        <Stat label="going (heads)" value={row.goingCount} />
      </div>
    </>
  );

  if (!linkable) {
    return (
      <div className="border-border bg-surface flex items-center justify-between gap-3 rounded-lg border p-3">
        {content}
      </div>
    );
  }

  return (
    <Link
      to={`/events/${row.eventId}/report`}
      className="border-border bg-surface hover:bg-surface-dim flex items-center justify-between gap-3 rounded-lg border p-3 transition-colors"
    >
      {content}
    </Link>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <span className="bg-surface-dim text-foreground-secondary rounded-full px-2.5 py-0.5">
      <span className="text-foreground font-medium">{value}</span> {label}
    </span>
  );
}
