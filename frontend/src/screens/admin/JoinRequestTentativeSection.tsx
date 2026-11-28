import { Link } from 'react-router-dom';

import type { JoinRequestRsvpEvent, JoinRequestSummary } from '@/api/join';
import { Button } from '@/components/ui/Button';
import { EVENT_TZ_LABEL, formatEventTime } from '@/utils/datetime';

export function TentativeActions({
  request,
  busy,
  onApprove,
  onResend,
}: {
  request: JoinRequestSummary;
  busy: boolean;
  onApprove: () => void;
  onResend: () => void;
}) {
  return (
    <div className="mt-3 flex flex-col gap-3">
      <RsvpEventList events={request.rsvpEvents} />
      <div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={onApprove} disabled={busy}>
            manually approve
          </Button>
          {request.onboardedAt === null ? (
            <Button variant="secondary" onClick={onResend} disabled={busy}>
              re-send welcome
            </Button>
          ) : null}
        </div>
        <p className="text-muted mt-2 text-xs">
          tentative members can&rsquo;t be rejected — archive them from the{' '}
          {request.userId ? (
            <Link to={`/admin/members/${request.userId}`} className="underline">
              members screen
            </Link>
          ) : (
            'members screen'
          )}{' '}
          instead
        </p>
      </div>
    </div>
  );
}

function RsvpEventList({ events }: { events: JoinRequestRsvpEvent[] }) {
  if (events.length === 0) return null;
  return (
    <div>
      <p className="text-muted text-xs font-medium">rsvp&rsquo;d to</p>
      <ul className="mt-1 flex flex-col gap-0.5">
        {events.map((e) => (
          <li key={e.eventId} className="text-foreground-secondary text-xs">
            {e.title}
            {e.startDatetime
              ? ` · ${formatEventTime(new Date(e.startDatetime), 'MMM d, h:mm a')} ${EVENT_TZ_LABEL}`
              : ''}
          </li>
        ))}
      </ul>
    </div>
  );
}
