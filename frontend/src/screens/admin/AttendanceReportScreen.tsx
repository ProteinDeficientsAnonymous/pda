// Admin: /admin/attendance — cross-event attendance report built on the
// existing per-event check-in. Shows, per event, how many people attended /
// no-showed out of the going rsvps. Gated by manage_events (route + backend).

import { format } from 'date-fns';
import { Link } from 'react-router-dom';
import { useAttendanceReport, type EventAttendanceRow } from '@/api/attendanceReport';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function AttendanceReportScreen() {
  const { data = [], isPending, isError } = useAttendanceReport();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load attendance — try refreshing" />;

  return (
    <ContentContainer>
      <header className="mb-4">
        <h1 className="mb-1 text-2xl font-medium tracking-tight">attendance</h1>
        <p className="text-muted text-sm">who actually showed up, per event</p>
      </header>

      {data.length === 0 ? (
        <p className="text-muted text-sm">no attendance marked yet 🌿</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {data.map((row) => (
            <li key={row.eventId}>
              <AttendanceRow row={row} />
            </li>
          ))}
        </ul>
      )}
    </ContentContainer>
  );
}

function AttendanceRow({ row }: { row: EventAttendanceRow }) {
  return (
    <Link
      to={`/events/${row.eventId}`}
      className="border-border bg-surface hover:bg-surface-dim flex items-center justify-between gap-3 rounded-lg border p-3 transition-colors"
    >
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
        <Stat label="going" value={row.goingCount} />
      </div>
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
