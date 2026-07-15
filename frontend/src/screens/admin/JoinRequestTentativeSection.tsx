import { format } from 'date-fns';

import type { JoinRequestRsvpEvent, JoinRequestSummary } from '@/api/join';
import { Button } from '@/components/ui/Button';

export function TentativeActions({
  request,
  busy,
  onApprove,
}: {
  request: JoinRequestSummary;
  busy: boolean;
  onApprove: () => void;
}) {
  return (
    <div className="mt-3 flex flex-col gap-3">
      <RsvpEventList events={request.rsvpEvents} />
      <div>
        <Button onClick={onApprove} disabled={busy}>
          manually approve
        </Button>
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
              ? ` · ${format(new Date(e.startDatetime), 'MMM d, h:mm a').toLowerCase()}`
              : ''}
          </li>
        ))}
      </ul>
    </div>
  );
}
