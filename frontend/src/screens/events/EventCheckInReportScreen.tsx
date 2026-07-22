import { type ReactNode, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { extractApiError, getApiStatus } from '@/api/apiErrors';
import type { AttendedPerson, CanceledPerson, CheckInReportPerson } from '@/api/eventCheckInReport';
import { useCheckInReport } from '@/api/eventCheckInReport';
import { useEvent } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { canManageEvent } from '@/models/event';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { formatShortDateTime } from '@/utils/datetime';

import { CheckInReportCsvSheet } from './CheckInReportCsvSheet';

export default function EventCheckInReportScreen() {
  const { id } = useParams<{ id: string }>();
  const user = useAuthStore((s) => s.user);
  const { data: event, isPending, isError, error } = useEvent(id);
  const [csvOpen, setCsvOpen] = useState(false);

  const isHost = event ? canManageEvent(event, user) : false;
  const report = useCheckInReport(isHost ? id : undefined);

  if (isPending) return <ContentLoading />;
  if (isError) {
    if (getApiStatus(error) === 403) {
      const message = extractApiError(error) ?? "you don't have permission to see this event";
      return <ForbiddenNotice eventId={id} message={message} />;
    }
    return <ContentError message="couldn't load this event — try refreshing" />;
  }

  if (!canManageEvent(event, user)) {
    return (
      <ForbiddenNotice
        eventId={event.id}
        message="only the host or a co-host can see the check-in report"
      />
    );
  }

  return (
    <ContentContainer>
      <BackLink eventId={event.id} />
      <div className="mb-6 flex items-start justify-between gap-2">
        <div>
          <h1 className="mb-1 text-2xl font-medium tracking-tight">check-in report</h1>
          <p className="text-foreground-secondary text-sm">{event.title}</p>
        </div>
        <Button
          variant="secondary"
          onClick={() => {
            setCsvOpen(true);
          }}
        >
          export csv
        </Button>
      </div>

      {report.isLoading ? <p className="text-muted text-sm">loading report…</p> : null}
      {report.isError ? (
        <p className="text-sm text-red-600">couldn't load the report — try refreshing</p>
      ) : null}
      {report.data ? <ReportBody report={report.data} /> : null}

      <CheckInReportCsvSheet
        eventId={event.id}
        open={csvOpen}
        onClose={() => {
          setCsvOpen(false);
        }}
      />
    </ContentContainer>
  );
}

function ReportBody({
  report,
}: {
  report: NonNullable<ReturnType<typeof useCheckInReport>['data']>;
}) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap gap-2 text-xs">
        <Pill label="attended" value={report.attendedCount} />
        <Pill label="no-show" value={report.noShowCount} />
        <Pill label="canceled" value={report.canceledCount} />
        <Pill label="unmarked" value={report.unmarkedCount} />
      </div>

      <PersonSection title="attended" people={report.attended} empty="nobody checked in">
        {(p) => <AttendedRow key={p.userId} person={p} />}
      </PersonSection>

      <PersonSection title="no-shows" people={report.noShows} empty="no no-shows">
        {(p) => <PersonRow key={p.userId} person={p} />}
      </PersonSection>

      <PersonSection title="canceled" people={report.canceled} empty="nobody canceled">
        {(p) => <CanceledRow key={p.userId} person={p} />}
      </PersonSection>

      <PersonSection title="unmarked" people={report.unmarked} empty="everyone got marked">
        {(p) => <PersonRow key={p.userId} person={p} />}
      </PersonSection>
    </div>
  );
}

function Pill({ label, value }: { label: string; value: number }) {
  return (
    <span className="bg-surface-dim text-foreground-secondary rounded-full px-3 py-1">
      <span className="text-foreground font-medium">{value}</span> {label}
    </span>
  );
}

function PersonSection<T extends CheckInReportPerson>({
  title,
  people,
  empty,
  children,
}: {
  title: string;
  people: T[];
  empty: string;
  children: (person: T) => ReactNode;
}) {
  return (
    <section>
      <h2 className="text-muted mb-2 text-xs font-medium">{title}</h2>
      {people.length === 0 ? (
        <p className="text-muted text-xs">{empty}</p>
      ) : (
        <ul className="flex flex-col gap-2">{people.map(children)}</ul>
      )}
    </section>
  );
}

function GuestBadge() {
  return <span className="bg-surface-dim text-foreground-secondary rounded px-1.5 py-0.5">guest</span>;
}

function PersonRow({ person }: { person: CheckInReportPerson }) {
  return (
    <li className="border-border flex items-center justify-between gap-2 rounded-md border p-2 text-sm">
      <span className="flex items-center gap-2">
        {person.name}
        {!person.isMember ? <GuestBadge /> : null}
      </span>
    </li>
  );
}

function AttendedRow({ person }: { person: AttendedPerson }) {
  return (
    <li className="border-border flex items-center justify-between gap-2 rounded-md border p-2 text-sm">
      <span className="flex items-center gap-2">
        {person.name}
        {!person.isMember ? <GuestBadge /> : null}
      </span>
      {person.checkedInAt ? (
        <span className="text-muted text-xs">{formatShortDateTime(person.checkedInAt)}</span>
      ) : null}
    </li>
  );
}

function CanceledRow({ person }: { person: CanceledPerson }) {
  return (
    <li className="border-border flex items-center justify-between gap-2 rounded-md border p-2 text-sm">
      <span className="flex items-center gap-2">
        {person.name}
        {!person.isMember ? <GuestBadge /> : null}
      </span>
      <span className="text-muted text-xs">canceled {formatShortDateTime(person.cancelledAt)}</span>
    </li>
  );
}

function BackLink({ eventId }: { eventId: string }) {
  return (
    <Link
      to={`/events/${eventId}`}
      className="text-foreground-secondary hover:text-foreground mb-4 inline-flex items-center gap-1 text-sm"
    >
      ← back to event
    </Link>
  );
}

function ForbiddenNotice({ eventId, message }: { eventId: string | undefined; message: string }) {
  return (
    <ContentContainer>
      <section className="border-border bg-surface mt-8 rounded-lg border p-6">
        <h2 className="mb-2 text-base font-medium">{message}</h2>
        <Link
          to={eventId ? `/events/${eventId}` : '/calendar'}
          className="border-border-strong text-foreground-secondary hover:bg-background mt-4 inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium"
        >
          back to event
        </Link>
      </section>
    </ContentContainer>
  );
}
